"""Framing-preview geometry: what a target looks like in the rig's frame.

`framing.framing_score` boils "does it fit" down to one number; this
module lays out the same geometry spatially, for a front end to draw —
the rig's field of view as a rectangle around the target (or a group's
centroid), every catalog object that lands inside it, and how the frame
sits on the sky at a given moment. Pure geometry, no rendering and no
I/O: like `charting.py`, it only produces numbers; drawing them (and any
optional survey image underneath) is the renderer's own job.

Coordinates are a gnomonic (TAN) projection around the frame center, in
arcmin: `east_arcmin` positive toward east, `north_arcmin` positive
toward north — the usual sky-chart convention is north up, east *left*,
so a renderer flips the east axis when it draws.

Frame orientation: an alt-az mount keeps the sensor level with the
horizon, so the frame's "up" edge points toward the zenith, whose
position angle (north through east) on the sky is the parallactic angle
— hence `frame_angle_deg`, which keeps changing over a session (see
`framing.field_rotation_rate_deg_per_min`). An eq mount tracks the
sky's own rotation, so its frame stays fixed; this module assumes the
usual setup with the sensor's long side along RA (angle 0) — the engine
doesn't model camera rotation on an eq mount.

The sensor's width is taken as the horizontal side (landscape), matching
`Rig.fov_deg`'s (width, height) order.

Since an alt-az frame keeps turning, a preview drawn at one moment only
tells part of the story: given the night's dark window, `orientation_track`
adds the frame angle at every full hour of it while the target clears the
planner's minimum altitude — how far the frame turns before and after the
moment drawn.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from astropy import units as u
from astropy.coordinates import ICRS, AltAz, SkyCoord
from astropy.time import Time

from nachtlotse.engine import ephemeris, framing, grouping
from nachtlotse.engine.constraints import (
    DEFAULT_MIN_ALT_DEG,
    build_fixed_target,
    build_observer,
)
from nachtlotse.engine.models import Rig, Site, Target

# How far `frame_angle_deg` steps toward the zenith to read off the "up"
# direction — small enough to stay a local direction, far above
# floating-point noise.
_ZENITH_NUDGE = 1.0 * u.arcmin


@dataclass(frozen=True)
class FramedObject:
    """One catalog object placed in the frame."""

    target: Target
    east_arcmin: float
    north_arcmin: float
    # True for the target(s) the preview was asked for, False for catalog
    # neighbors that merely happen to fall inside the frame.
    primary: bool

    @property
    def size_known(self) -> bool:
        return self.target.size_arcmin != (0.0, 0.0)


@dataclass(frozen=True)
class FrameOrientation:
    """The frame's orientation at one moment of the night."""

    when: datetime
    frame_angle_deg: float
    alt_deg: float


@dataclass(frozen=True)
class FramingPreview:
    when: datetime
    center_ra_deg: float
    center_dec_deg: float
    fov_width_arcmin: float
    fov_height_arcmin: float
    # Position angle (north through east) of the frame's "up" edge
    # direction: the parallactic angle for an alt-az mount, 0.0 for eq.
    frame_angle_deg: float
    # The frame rectangle's four corners, (east_arcmin, north_arcmin),
    # in drawing order.
    frame_corners: tuple[tuple[float, float], ...]
    # None for an eq mount, which has no field rotation.
    rotation_rate_deg_per_min: float | None
    # The span framing fit is scored on: a single target's major axis, or
    # a group's largest pairwise separation. 0.0 = unknown size.
    span_arcmin: float
    # span / FoV short side — None when the span is unknown.
    fill_fraction: float | None
    # Exactly the value ranking used (`framing.fill_fraction_score`).
    fit: float
    objects: tuple[FramedObject, ...]
    # Hourly orientations across the night (see `orientation_track`) —
    # empty for an eq mount, or when no night was given.
    orientation_track: tuple[FrameOrientation, ...] = ()


def gnomonic_offset_arcmin(
    center_ra_deg: float, center_dec_deg: float, ra_deg: float, dec_deg: float
) -> tuple[float, float] | None:
    """(east_arcmin, north_arcmin) of a position in the tangent plane
    around a center; None if it lies on the far hemisphere, where the
    projection is undefined."""
    ra0 = math.radians(center_ra_deg)
    dec0 = math.radians(center_dec_deg)
    ra = math.radians(ra_deg)
    dec = math.radians(dec_deg)
    d_ra = ra - ra0

    cos_c = math.sin(dec0) * math.sin(dec) + math.cos(dec0) * math.cos(dec) * math.cos(
        d_ra
    )
    if cos_c <= 0.0:
        return None
    xi = math.cos(dec) * math.sin(d_ra) / cos_c
    eta = (
        math.cos(dec0) * math.sin(dec) - math.sin(dec0) * math.cos(dec) * math.cos(d_ra)
    ) / cos_c
    return math.degrees(xi) * 60.0, math.degrees(eta) * 60.0


def frame_angle_deg(rig: Rig, site: Site, target: Target, when: datetime) -> float:
    """The frame's "up" position angle on the sky, in (-180, 180] — see
    the module docstring.

    For an alt-az mount: the ICRS position angle of the direction from
    the target straight up toward the zenith, taken by nudging the
    target's alt-az position upward and transforming it back. That's the
    parallactic angle by definition, but measured against ICRS north (the
    north a survey image is drawn with) and with precession/nutation
    handled by astropy — astroplan's own `parallactic_angle` derives the
    hour angle from J2000 RA directly, which is off by up to a couple of
    degrees near the zenith, where the angle changes fastest.
    """
    if rig.mount.kind != "altaz":
        return 0.0
    location = build_observer(site).location
    altaz_frame = AltAz(obstime=Time(when), location=location)
    coord = build_fixed_target(target).coord
    pos = coord.transform_to(altaz_frame)
    above = SkyCoord(alt=pos.alt + _ZENITH_NUDGE, az=pos.az, frame=altaz_frame)
    q_deg = float(coord.position_angle(above.transform_to(ICRS())).deg)
    wrapped = (q_deg + 180.0) % 360.0 - 180.0
    return 180.0 if wrapped == -180.0 else wrapped


def orientation_track(
    rig: Rig,
    site: Site,
    target: Target,
    night_start: datetime,
    night_end: datetime,
    *,
    min_alt_deg: float = DEFAULT_MIN_ALT_DEG,
) -> tuple[FrameOrientation, ...]:
    """The frame angle at every full hour within [night_start, night_end]
    (typically `constraints.dark_window`) at which `target` stands at
    least `min_alt_deg` high — below that the planner wouldn't shoot it,
    so its orientation there means nothing. Empty for an eq mount, whose
    frame doesn't turn."""
    if rig.mount.kind != "altaz":
        return ()
    hour = night_start.replace(minute=0, second=0, microsecond=0)
    if hour < night_start:
        hour += timedelta(hours=1)
    track: list[FrameOrientation] = []
    while hour <= night_end:
        alt_deg = ephemeris.altaz(site, target, hour).alt_deg
        if alt_deg >= min_alt_deg:
            track.append(
                FrameOrientation(
                    hour, frame_angle_deg(rig, site, target, hour), alt_deg
                )
            )
        hour += timedelta(hours=1)
    return tuple(track)


def frame_corners(
    fov_width_arcmin: float, fov_height_arcmin: float, angle_deg: float
) -> tuple[tuple[float, float], ...]:
    """The frame rectangle's corners in (east, north) arcmin, rotated so
    its "up" edge direction sits at `angle_deg` (north through east)."""
    angle_rad = math.radians(angle_deg)
    up = (math.sin(angle_rad), math.cos(angle_rad))
    side = (math.cos(angle_rad), -math.sin(angle_rad))
    half_w = fov_width_arcmin / 2.0
    half_h = fov_height_arcmin / 2.0
    return tuple(
        (
            s * half_w * side[0] + u * half_h * up[0],
            s * half_w * side[1] + u * half_h * up[1],
        )
        for s, u in ((-1, 1), (1, 1), (1, -1), (-1, -1))
    )


def _inside_frame(
    east_arcmin: float,
    north_arcmin: float,
    fov_width_arcmin: float,
    fov_height_arcmin: float,
    angle_deg: float,
) -> bool:
    angle_rad = math.radians(angle_deg)
    along_up = east_arcmin * math.sin(angle_rad) + north_arcmin * math.cos(angle_rad)
    along_side = east_arcmin * math.cos(angle_rad) - north_arcmin * math.sin(angle_rad)
    return (
        abs(along_side) <= fov_width_arcmin / 2.0
        and abs(along_up) <= fov_height_arcmin / 2.0
    )


def framing_preview(
    site: Site,
    rig: Rig,
    targets: Sequence[Target],
    when: datetime,
    *,
    neighbors: Sequence[Target] = (),
    night: tuple[datetime, datetime] | None = None,
) -> FramingPreview:
    """Lay out `targets` (one target, or a co-visible group) in `rig`'s
    frame at `when`, plus any of `neighbors` (typically the whole catalog
    — the engine never loads it itself) whose position falls inside the
    frame. Given `night` (the dark window's start and end), also the
    hourly `orientation_track` across it. Raises ValueError for an empty
    `targets`.
    """
    if not targets:
        raise ValueError("framing_preview needs at least one target")

    center = targets[0] if len(targets) == 1 else grouping.centroid_target(targets)
    fov_width_deg, fov_height_deg = rig.fov_deg
    fov_width_arcmin = fov_width_deg * 60.0
    fov_height_arcmin = fov_height_deg * 60.0
    angle_deg = frame_angle_deg(rig, site, center, when)

    objects: list[FramedObject] = []
    for target in targets:
        offset = gnomonic_offset_arcmin(
            center.ra_deg, center.dec_deg, target.ra_deg, target.dec_deg
        )
        # A co-visible group's members all sit within one FoV of the
        # centroid, so the projection is always defined for them.
        assert offset is not None
        objects.append(FramedObject(target, offset[0], offset[1], primary=True))
    for neighbor in neighbors:
        if neighbor in targets:
            continue
        offset = gnomonic_offset_arcmin(
            center.ra_deg, center.dec_deg, neighbor.ra_deg, neighbor.dec_deg
        )
        if offset is not None and _inside_frame(
            *offset, fov_width_arcmin, fov_height_arcmin, angle_deg
        ):
            objects.append(FramedObject(neighbor, offset[0], offset[1], primary=False))

    if len(targets) == 1:
        span_arcmin = targets[0].size_arcmin[0]
    else:
        span_arcmin = grouping.group_span_arcmin(targets)
    fov_short = framing.fov_short_arcmin(rig)

    return FramingPreview(
        when=when,
        center_ra_deg=center.ra_deg,
        center_dec_deg=center.dec_deg,
        fov_width_arcmin=fov_width_arcmin,
        fov_height_arcmin=fov_height_arcmin,
        frame_angle_deg=angle_deg,
        frame_corners=frame_corners(fov_width_arcmin, fov_height_arcmin, angle_deg),
        rotation_rate_deg_per_min=(
            framing.field_rotation_rate_deg_per_min(site, center, when)
            if rig.mount.kind == "altaz"
            else None
        ),
        span_arcmin=span_arcmin,
        fill_fraction=span_arcmin / fov_short if span_arcmin > 0.0 else None,
        fit=framing.fill_fraction_score(span_arcmin, fov_short),
        objects=tuple(objects),
        orientation_track=(
            orientation_track(rig, site, center, *night) if night is not None else ()
        ),
    )

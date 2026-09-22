"""Polar (alt/az) projection geometry for the shortlist-overview chart.

Used by the CLI's PNG export (`chart_export.py`, rendered with
matplotlib) and kept independent of any one charting library — this
module only produces plain (x, y) points; drawing them is the
renderer's own job. A future UI could reuse it the same way.

No new astronomy here: altitude/azimuth still comes from
`engine.ephemeris` and `HorizonProfile.min_alt`, this just projects
those numbers onto a 2D plot — zenith at the center (r=0), the true
horizon at the rim (r=90), azimuth clockwise from north at the top
(the usual compass convention: N top, E right, S bottom, W left).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from nachtlotse.engine import ephemeris, grouping
from nachtlotse.engine.models import Site, Target
from nachtlotse.planning import NightPlan, RankedGroup

# Zenith-distance rings drawn as chart grid lines, in degrees of altitude.
GRID_RINGS_ALT_DEG = (0.0, 20.0, 40.0, 60.0, 80.0)

# Azimuth (compass) directions labeled at the rim.
COMPASS_LABELS: tuple[tuple[str, float], ...] = (
    ("N", 0.0),
    ("E", 90.0),
    ("S", 180.0),
    ("W", 270.0),
)

_HORIZON_RESOLUTION_DEG = 2.0
_RING_RESOLUTION_DEG = 3.0

# Validated categorical palette (dataviz skill's palette.md, light-mode
# steps, slots 1-5 — CVD-safe on the adjacent-pairlist up to 5 series).
# Covers every shortlist in the common case (SHORTLIST_SIZE = 5 targets
# max) — a favorite folded in beyond that cutoff (ROADMAP.md's
# "Favorites in the catalog") can push a shortlist past 5, in which case
# whichever renderer uses this cycles back to the first color instead of
# erroring (sky_chart.py's `_track_color` does exactly that).
SHORTLIST_PALETTE = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4")

# Muted, recessive chrome — grid rings and the horizon-blocked wedge —
# from the same palette's "chart chrome" table, not the categorical set.
GRID_COLOR = "#c3c2b7"
LABEL_COLOR = "#898781"
HORIZON_FILL_COLOR = "#c3c2b7"


def project(alt_deg: float, az_deg: float) -> tuple[float, float]:
    """Alt/az -> (x, y): zenith distance as radius, azimuth as compass
    angle (clockwise from north, north at the top)."""
    r = 90.0 - alt_deg
    az_rad = math.radians(az_deg)
    return r * math.sin(az_rad), r * math.cos(az_rad)


@dataclass(frozen=True)
class Track:
    """One shortlisted target's alt/az path across the dark window.

    Split into `segments` rather than one flat point list: a target
    that dips below the horizon partway through the window must not
    have its two above-horizon arcs joined by a straight line drawn
    through the ground.
    """

    name: str
    segments: list[list[tuple[float, float]]]


def _entry_targets(entry: object) -> tuple[Target, ...]:
    """The one or more real catalog targets behind a shortlist entry —
    a `RankedGroup`'s members, or a single-target entry's own target."""
    if isinstance(entry, RankedGroup):
        return entry.targets
    return (entry.target,)


def _entry_name(entry: object) -> str:
    targets = _entry_targets(entry)
    return " + ".join(t.name for t in targets)


def _entry_track_target(entry: object) -> Target:
    """The single position to plot this shortlist entry's track from —
    a `RankedGroup`'s centroid (members are co-visible/close together by
    construction, see `engine.grouping.co_visible_group`, so their own
    curves would nearly overlap anyway; one line reads far better than
    stacking every member's near-identical curve), or a single-target
    entry's own target otherwise."""
    if isinstance(entry, RankedGroup):
        return grouping.centroid_target(entry.targets)
    return entry.target


def shortlist_tracks(plan: NightPlan, num_samples: int = 49) -> list[Track]:
    """One `Track` per shortlisted entry — a single line even for a
    `RankedGroup` (see `_entry_track_target`) — points clipped to alt >=
    0 (below the true horizon isn't part of the visible sky dome)."""
    tracks = []
    for entry in plan.shortlist:
        target = _entry_track_target(entry.ranked)
        series = ephemeris.altitude_series(
            plan.site,
            target,
            plan.evening_start,
            plan.morning_end,
            num_samples=num_samples,
        )
        segments: list[list[tuple[float, float]]] = []
        current: list[tuple[float, float]] = []
        for _when, pos in series:
            if pos.alt_deg >= 0.0:
                current.append(project(pos.alt_deg, pos.az_deg))
            elif current:
                segments.append(current)
                current = []
        if current:
            segments.append(current)
        tracks.append(Track(name=_entry_name(entry.ranked), segments=segments))
    return tracks


def moon_track(
    site: Site, evening_start: datetime, morning_end: datetime, num_samples: int = 49
) -> Track:
    """The Moon's own alt/az path across the dark window, clipped to
    alt >= 0 exactly like `shortlist_tracks` — a real, computed position
    (`engine.ephemeris.moon_altaz_series`), not a target from the
    catalog, so this stays a standalone function rather than another
    branch inside `shortlist_tracks`."""
    series = ephemeris.moon_altaz_series(
        site, evening_start, morning_end, num_samples=num_samples
    )
    segments: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for _when, pos in series:
        if pos.alt_deg >= 0.0:
            current.append(project(pos.alt_deg, pos.az_deg))
        elif current:
            segments.append(current)
            current = []
    if current:
        segments.append(current)
    return Track(name="Moon", segments=segments)


def grid_ring(
    alt_deg: float, resolution_deg: float = _RING_RESOLUTION_DEG
) -> list[tuple[float, float]]:
    """A full-circle zenith-distance ring at a given altitude, for the
    chart's background grid."""
    num_points = round(360.0 / resolution_deg) + 1
    return [project(alt_deg, az) for az in np.linspace(0.0, 360.0, num_points)]


def horizon_wedge(
    site: Site, resolution_deg: float = _HORIZON_RESOLUTION_DEG
) -> list[tuple[float, float]]:
    """A single closed polygon (outer rim, then the horizon-profile
    boundary in reverse) — fill it to shade the horizon-blocked region
    straight from `HorizonProfile.min_alt(az)`."""
    num_points = round(360.0 / resolution_deg) + 1
    azimuths = np.linspace(0.0, 360.0, num_points)
    outer = [project(0.0, az) for az in azimuths]
    inner = [
        project(site.horizon.min_alt(az), az) for az in reversed(azimuths.tolist())
    ]
    return outer + inner


def compass_label_point(az_deg: float, rim_r: float = 90.0) -> tuple[float, float]:
    """Where to place a compass-direction label just outside the rim."""
    return project(90.0 - rim_r, az_deg)

"""Twilight, moon, and horizon constraints — is a target worth shooting tonight?

Twilight/moon/altitude gating is built on astroplan/astropy: astroplan ships
the exact building blocks M1 called for (`AltitudeConstraint`,
`AtNightConstraint`, `MoonSeparationConstraint`, `observability_table`).
Horizon-profile clearance (M2) has no astroplan equivalent — `HorizonProfile`
is this project's own model — so `best_time_tonight` samples the night with
the skyfield-based `ephemeris` module instead and checks each sample against
`site.horizon.min_alt(az)` directly. Kept fully offline throughout — IERS
auto-download is disabled; the bundled `astropy-iers-data` package is
precise enough for twilight/moon timing, and no network access is needed at
a dark site.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from datetime import UTC, datetime

import numpy as np
from astroplan import (
    AltitudeConstraint,
    AtNightConstraint,
    FixedTarget,
    MoonSeparationConstraint,
    Observer,
    observability_table,
)
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord, get_body
from astropy.coordinates.errors import NonRotationTransformationWarning
from astropy.time import Time
from astropy.utils import iers

from nachtlotse.engine import ephemeris
from nachtlotse.engine.models import Site, Target

iers.conf.auto_download = False

# Separation constraints on a FixedTarget vs. the (fast-moving) Moon trigger
# an ICRS->GCRS frame transform that astropy flags as direction-dependent.
# The effect is negligible at arcsecond level, far below what matters here.
warnings.filterwarnings("ignore", category=NonRotationTransformationWarning)

_DEFAULT_MIN_ALT_DEG = 20.0
_DEFAULT_MIN_MOON_SEP_DEG = 30.0
_SAMPLES_PER_NIGHT = 25


def build_observer(site: Site) -> Observer:
    return Observer(
        latitude=site.lat_deg * u.deg,
        longitude=site.lon_deg * u.deg,
        elevation=site.elevation_m * u.m,
        name=site.name,
    )


def build_fixed_target(target: Target) -> FixedTarget:
    coord = SkyCoord(ra=target.ra_deg * u.deg, dec=target.dec_deg * u.deg, frame="icrs")
    return FixedTarget(coord=coord, name=target.name)


def _earth_location(site: Site) -> EarthLocation:
    return EarthLocation(
        lat=site.lat_deg * u.deg,
        lon=site.lon_deg * u.deg,
        height=site.elevation_m * u.m,
    )


def _moon_separation_deg(site: Site, target: Target, when: datetime) -> float:
    moon = get_body("moon", Time(when), _earth_location(site))
    target_coord = SkyCoord(ra=target.ra_deg * u.deg, dec=target.dec_deg * u.deg)
    return float(moon.separation(target_coord).deg)


def clears_horizon(site: Site, pos: ephemeris.AltAz) -> bool:
    """Whether a position sits above the site's horizon profile."""
    return bool(pos.alt_deg > site.horizon.min_alt(pos.az_deg))


def dark_window(site: Site, reference: datetime) -> tuple[datetime, datetime]:
    """Astronomical-twilight dark window (sun below -18°) around `reference`.

    If `reference` falls within a night, returns that night's window;
    otherwise returns the next upcoming one.
    """
    observer = build_observer(site)
    t_ref = Time(reference)

    evening_start = observer.twilight_evening_astronomical(t_ref, which="previous")
    morning_end = observer.twilight_morning_astronomical(evening_start, which="next")

    if t_ref > morning_end:
        evening_start = observer.twilight_evening_astronomical(t_ref, which="next")
        morning_end = observer.twilight_morning_astronomical(
            evening_start, which="next"
        )

    return (
        evening_start.to_datetime(timezone=UTC),
        morning_end.to_datetime(timezone=UTC),
    )


def is_observable_tonight(
    site: Site,
    target: Target,
    reference: datetime,
    *,
    min_alt_deg: float = _DEFAULT_MIN_ALT_DEG,
    min_moon_sep_deg: float = _DEFAULT_MIN_MOON_SEP_DEG,
) -> bool:
    """Whether the target ever clears altitude/night/moon-separation
    constraints during tonight's astronomical-twilight dark window.
    """
    evening_start, morning_end = dark_window(site, reference)
    observer = build_observer(site)
    times = Time(
        np.linspace(Time(evening_start).jd, Time(morning_end).jd, _SAMPLES_PER_NIGHT),
        format="jd",
    )

    night_constraints = [
        AltitudeConstraint(min=min_alt_deg * u.deg),
        AtNightConstraint.twilight_astronomical(),
        MoonSeparationConstraint(min=min_moon_sep_deg * u.deg),
    ]

    table = observability_table(
        night_constraints, observer, [build_fixed_target(target)], times=times
    )
    return bool(table["ever observable"][0])


def best_time_tonight(
    site: Site,
    target: Target,
    reference: datetime,
    *,
    min_alt_deg: float = _DEFAULT_MIN_ALT_DEG,
    min_moon_sep_deg: float = _DEFAULT_MIN_MOON_SEP_DEG,
    extra_ok: Callable[[datetime, ephemeris.AltAz], bool] | None = None,
) -> tuple[datetime, ephemeris.AltAz] | None:
    """The best (highest-altitude) moment tonight that clears altitude,
    the site's horizon profile, and moon separation — or None if there
    isn't one.

    `is_observable_tonight` is a cheap pre-check (night/altitude/moon, no
    horizon); this only runs the finer per-sample horizon search once that
    passes, since a target the site's horizon blocks everywhere it would
    otherwise be observable is a real "no", not caught by the pre-check.

    `extra_ok`, if given, is an additional per-sample gate (e.g. rig-aware
    field-rotation safety from `engine.framing`) — kept as an injected
    callback rather than a parameter here so this module stays rig-agnostic
    and doesn't need to import `framing` (which itself imports the
    `build_observer`/`build_fixed_target` helpers below).
    """
    if not is_observable_tonight(
        site,
        target,
        reference,
        min_alt_deg=min_alt_deg,
        min_moon_sep_deg=min_moon_sep_deg,
    ):
        return None

    evening_start, morning_end = dark_window(site, reference)
    start_jd = Time(evening_start).jd
    end_jd = Time(morning_end).jd

    best: tuple[datetime, ephemeris.AltAz] | None = None
    for sample_jd in np.linspace(start_jd, end_jd, _SAMPLES_PER_NIGHT):
        sample_time = Time(sample_jd, format="jd").to_datetime(timezone=UTC)
        pos = ephemeris.altaz(site, target, sample_time)

        if pos.alt_deg < min_alt_deg:
            continue
        if not clears_horizon(site, pos):
            continue
        if _moon_separation_deg(site, target, sample_time) < min_moon_sep_deg:
            continue
        if extra_ok is not None and not extra_ok(sample_time, pos):
            continue
        if best is None or pos.alt_deg > best[1].alt_deg:
            best = (sample_time, pos)

    return best

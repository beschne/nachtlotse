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

Performance: ranking the whole catalog asks the same night-level
questions once per target — the dark window, and the Sun and Moon at each
of the night's samples. Those are computed once per site and night
(`_night_samples`, memoized on plain values, so every function here stays
pure) and reused; each target's own samples are evaluated as one
vectorized batch instead of one astropy call per sample. Same inputs, same
math, same results — just without recomputing the sky for every target.
"""

from __future__ import annotations

import functools
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
from astroplan import FixedTarget, Observer
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord, get_body, get_sun
from astropy.coordinates.errors import NonRotationTransformationWarning
from astropy.time import Time
from astropy.utils import iers

from nachtlotse.engine import ephemeris
from nachtlotse.engine.models import Site, Target

iers.conf.auto_download = False
# The bundled IERS table ages; astropy raises once its predictions are >30 days
# old. UT1-UTC drifts well under a second over months — irrelevant here — so a
# stale table must never block planning.
iers.conf.auto_max_age = None

# Separation constraints on a FixedTarget vs. the (fast-moving) Moon trigger
# an ICRS->GCRS frame transform that astropy flags as direction-dependent.
# The effect is negligible at arcsecond level, far below what matters here.
warnings.filterwarnings("ignore", category=NonRotationTransformationWarning)

DEFAULT_MIN_ALT_DEG = 20.0
DEFAULT_MIN_MOON_SEP_DEG = 30.0
_SAMPLES_PER_NIGHT = 25
# Astronomical twilight: the Sun at or below -18° (astroplan's
# `AtNightConstraint.twilight_astronomical`).
_MAX_SOLAR_ALT_DEG = -18.0


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


def moon_separation_deg(site: Site, target: Target, when: datetime) -> float:
    """Angular separation between `target` and the Moon at `when`.

    Unlike `engine.grouping.angular_separation_deg` (two fixed catalog
    positions), this tracks a moving body, so it needs `site` and
    `when`. Public because `planning`'s group-visibility gate checks it
    per group member, not just for the single target `best_time_tonight`
    itself is scanning.
    """
    moon = _moon_at(site.lat_deg, site.lon_deg, site.elevation_m, when)
    target_coord = SkyCoord(ra=target.ra_deg * u.deg, dec=target.dec_deg * u.deg)
    return float(moon.separation(target_coord).deg)


@functools.lru_cache(maxsize=4096)
def _moon_at(
    lat_deg: float, lon_deg: float, elevation_m: float, when: datetime
) -> SkyCoord:
    """The Moon (GCRS, as `get_body` returns it) seen from a location at
    `when` — memoized: group visibility checks ask for the same sample
    times over and over, once per member."""
    location = EarthLocation(
        lat=lat_deg * u.deg, lon=lon_deg * u.deg, height=elevation_m * u.m
    )
    return get_body("moon", Time(when), location)


def clears_horizon(site: Site, pos: ephemeris.AltAz) -> bool:
    """Whether a position sits above the site's horizon profile."""
    return bool(pos.alt_deg > site.horizon.min_alt(pos.az_deg))


def dark_window(site: Site, reference: datetime) -> tuple[datetime, datetime]:
    """Astronomical-twilight dark window (sun below -18°) around `reference`.

    If `reference` falls within a night, returns that night's window;
    otherwise returns the next upcoming one. Memoized per location and
    `reference` (see the module docstring): ranking asks this once per
    catalog target, always for the same night.
    """
    return _dark_window(site.lat_deg, site.lon_deg, site.elevation_m, reference)


@functools.lru_cache(maxsize=256)
def _dark_window(
    lat_deg: float, lon_deg: float, elevation_m: float, reference: datetime
) -> tuple[datetime, datetime]:
    observer = Observer(
        latitude=lat_deg * u.deg,
        longitude=lon_deg * u.deg,
        elevation=elevation_m * u.m,
    )
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


@dataclass(frozen=True)
class _NightSamples:
    """Everything about a night that's the same for every target: the
    sample times across the dark window, the Sun's altitude and the Moon's
    position at each of them."""

    times: Time
    datetimes: tuple[datetime, ...]
    sun_alt_deg: np.ndarray
    moon: SkyCoord


@functools.lru_cache(maxsize=64)
def _night_samples(
    lat_deg: float, lon_deg: float, elevation_m: float, reference: datetime
) -> _NightSamples:
    evening_start, morning_end = _dark_window(lat_deg, lon_deg, elevation_m, reference)
    times = Time(
        np.linspace(Time(evening_start).jd, Time(morning_end).jd, _SAMPLES_PER_NIGHT),
        format="jd",
    )
    observer = Observer(
        latitude=lat_deg * u.deg,
        longitude=lon_deg * u.deg,
        elevation=elevation_m * u.m,
    )
    # Same calls astroplan's AtNightConstraint/MoonSeparationConstraint make.
    sun_alt_deg = observer.altaz(times, get_sun(times)).alt.deg
    moon = get_body("moon", times, location=observer.location)
    datetimes = tuple(
        Time(jd, format="jd").to_datetime(timezone=UTC) for jd in times.jd
    )
    return _NightSamples(times, datetimes, np.asarray(sun_alt_deg), moon)


def _samples_for(site: Site, reference: datetime) -> _NightSamples:
    return _night_samples(site.lat_deg, site.lon_deg, site.elevation_m, reference)


def is_observable_tonight(
    site: Site,
    target: Target,
    reference: datetime,
    *,
    min_alt_deg: float = DEFAULT_MIN_ALT_DEG,
    min_moon_sep_deg: float = DEFAULT_MIN_MOON_SEP_DEG,
) -> bool:
    """Whether the target ever clears altitude/night/moon-separation
    constraints during tonight's astronomical-twilight dark window.

    The same test astroplan's `observability_table` runs with
    `AltitudeConstraint`, `AtNightConstraint.twilight_astronomical()` and
    `MoonSeparationConstraint` — the same astropy calls on the same sample
    times — but with the Sun and Moon computed once per night
    (`_night_samples`) instead of once per target.
    """
    observable, _moon_sep_deg = _observability(
        site, target, reference, min_alt_deg, min_moon_sep_deg
    )
    return observable


def _observability(
    site: Site,
    target: Target,
    reference: datetime,
    min_alt_deg: float,
    min_moon_sep_deg: float,
) -> tuple[bool, np.ndarray]:
    """`is_observable_tonight`'s answer, plus the target's Moon separation
    (deg) at each of the night's samples — which `best_time_tonight`
    needs too, so it's computed once and handed on rather than twice."""
    night = _samples_for(site, reference)
    observer = build_observer(site)
    fixed_target = build_fixed_target(target)
    target_alt_deg = observer.altaz(night.times, fixed_target).alt.deg
    # moon.separation(target), not the reverse: separation in the Moon's
    # own (GCRS) frame, exactly as MoonSeparationConstraint computes it.
    moon_sep_deg = np.asarray(night.moon.separation(fixed_target.coord).deg)
    observable = (
        (min_alt_deg <= target_alt_deg)
        & (night.sun_alt_deg <= _MAX_SOLAR_ALT_DEG)
        & (min_moon_sep_deg <= moon_sep_deg)
    )
    return bool(np.any(observable)), moon_sep_deg


def best_time_tonight(
    site: Site,
    target: Target,
    reference: datetime,
    *,
    min_alt_deg: float = DEFAULT_MIN_ALT_DEG,
    min_moon_sep_deg: float = DEFAULT_MIN_MOON_SEP_DEG,
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
    `build_observer`/`build_fixed_target` helpers below). It's by far the
    most expensive check, so it runs last and lazily: candidates that pass
    everything else are tried highest first, and the first one `extra_ok`
    accepts is the answer — the same sample a full scan would pick (ties
    go to the earlier sample, as before).
    """
    observable, moon_sep_deg = _observability(
        site, target, reference, min_alt_deg, min_moon_sep_deg
    )
    if not observable:
        return None

    night = _samples_for(site, reference)
    positions = ephemeris.altaz_at(site, target, night.datetimes)

    candidates = [
        i
        for i, pos in enumerate(positions)
        if pos.alt_deg >= min_alt_deg
        and clears_horizon(site, pos)
        and moon_sep_deg[i] >= min_moon_sep_deg
    ]
    # Highest first; `sorted` is stable, so equal altitudes keep time order.
    for i in sorted(candidates, key=lambda i: -positions[i].alt_deg):
        if extra_ok is None or extra_ok(night.datetimes[i], positions[i]):
            return night.datetimes[i], positions[i]
    return None

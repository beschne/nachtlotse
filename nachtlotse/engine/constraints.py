"""Twilight and moon constraints — is a target worth shooting tonight?

Built on astroplan/astropy rather than the skyfield-based `ephemeris` module:
astroplan already ships the exact building blocks this milestone calls for
(`AltitudeConstraint`, `AtNightConstraint`, `MoonSeparationConstraint`,
`observability_table`). Kept fully offline — IERS auto-download is disabled;
the bundled `astropy-iers-data` package is precise enough for twilight/moon
timing, and no network access is needed at a dark site.
"""

from __future__ import annotations

import warnings
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
from astropy.coordinates import SkyCoord
from astropy.coordinates.errors import NonRotationTransformationWarning
from astropy.time import Time
from astropy.utils import iers

from nachtlotse.engine.models import Site, Target

iers.conf.auto_download = False

# Separation constraints on a FixedTarget vs. the (fast-moving) Moon trigger
# an ICRS->GCRS frame transform that astropy flags as direction-dependent.
# The effect is negligible at arcsecond level, far below what matters here.
warnings.filterwarnings("ignore", category=NonRotationTransformationWarning)

_DEFAULT_MIN_ALT_DEG = 20.0
_DEFAULT_MIN_MOON_SEP_DEG = 30.0
_SAMPLES_PER_NIGHT = 25


def _observer(site: Site) -> Observer:
    return Observer(
        latitude=site.lat_deg * u.deg,
        longitude=site.lon_deg * u.deg,
        elevation=site.elevation_m * u.m,
        name=site.name,
    )


def _fixed_target(target: Target) -> FixedTarget:
    coord = SkyCoord(ra=target.ra_deg * u.deg, dec=target.dec_deg * u.deg, frame="icrs")
    return FixedTarget(coord=coord, name=target.name)


def dark_window(site: Site, reference: datetime) -> tuple[datetime, datetime]:
    """Astronomical-twilight dark window (sun below -18°) around `reference`.

    If `reference` falls within a night, returns that night's window;
    otherwise returns the next upcoming one.
    """
    observer = _observer(site)
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
    observer = _observer(site)
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
        night_constraints, observer, [_fixed_target(target)], times=times
    )
    return bool(table["ever observable"][0])

"""Constraint tests against independently derived expectations (M1 DoD)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from astropy import units as u
from astropy.coordinates import EarthLocation, get_body
from astropy.time import Time

from nachtlotse.engine import constraints
from nachtlotse.engine.models import HorizonProfile, Site, Target

BAD_HOMBURG = Site(
    name="Bad Homburg",
    lat_deg=50.2266,
    lon_deg=8.6180,
    elevation_m=190.0,
    tz="Europe/Berlin",
    horizon=HorizonProfile(points=[]),
)

# Always above the horizon at this latitude (dec > 90 - lat): a clean case
# with no dependence on the current moon phase.
CIRCUMPOLAR_TARGET = Target(name="Circumpolar test target", ra_deg=0.0, dec_deg=70.0)

# Never rises at this latitude (max altitude = 90 - lat + dec < 0): a clean
# negative case, again independent of the moon.
NEVER_RISES_TARGET = Target(name="Never-rises test target", ra_deg=0.0, dec_deg=-70.0)


def test_dark_window_has_a_plausible_positive_duration() -> None:
    reference = datetime(2026, 9, 12, 15, 0, tzinfo=UTC)
    evening_start, morning_end = constraints.dark_window(BAD_HOMBURG, reference)

    assert evening_start < morning_end
    duration = morning_end - evening_start
    assert timedelta(hours=2) < duration < timedelta(hours=14)


def test_dark_window_covers_reference_when_already_at_night() -> None:
    reference = datetime(2026, 9, 12, 23, 0, tzinfo=UTC)
    evening_start, morning_end = constraints.dark_window(BAD_HOMBURG, reference)

    assert evening_start <= reference <= morning_end


def test_never_rises_target_drops_out_regardless_of_moon() -> None:
    reference = datetime(2026, 9, 12, 15, 0, tzinfo=UTC)
    assert (
        constraints.is_observable_tonight(
            BAD_HOMBURG, NEVER_RISES_TARGET, reference, min_moon_sep_deg=0.0
        )
        is False
    )


def test_circumpolar_target_is_observable_when_moon_constraint_is_disabled() -> None:
    reference = datetime(2026, 9, 12, 15, 0, tzinfo=UTC)
    assert (
        constraints.is_observable_tonight(
            BAD_HOMBURG, CIRCUMPOLAR_TARGET, reference, min_moon_sep_deg=0.0
        )
        is True
    )


def test_target_coincident_with_the_moon_drops_out() -> None:
    """A target sitting exactly on the Moon's own position (zero separation)
    must fail any positive moon-separation constraint — independent of
    calendar-based full-moon assumptions.
    """
    reference = datetime(2026, 9, 12, 22, 0, tzinfo=UTC)
    evening_start, _ = constraints.dark_window(BAD_HOMBURG, reference)
    location = EarthLocation(
        lat=BAD_HOMBURG.lat_deg * u.deg,
        lon=BAD_HOMBURG.lon_deg * u.deg,
        height=BAD_HOMBURG.elevation_m * u.m,
    )
    moon = get_body("moon", Time(evening_start), location)
    moon_target = Target(
        name="Moon-coincident test target", ra_deg=moon.ra.deg, dec_deg=moon.dec.deg
    )

    assert (
        constraints.is_observable_tonight(
            BAD_HOMBURG, moon_target, reference, min_alt_deg=0.0, min_moon_sep_deg=30.0
        )
        is False
    )

"""Constraint tests against independently derived expectations (M1/M2 DoD)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
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


# A single-point profile makes `HorizonProfile.min_alt` return that altitude
# for every azimuth (see engine/models.py's wrap-around branch) — a uniform
# 90° wall, i.e. nothing is ever observable here regardless of direction.
WALLED_SITE = Site(
    name="Walled test site",
    lat_deg=BAD_HOMBURG.lat_deg,
    lon_deg=BAD_HOMBURG.lon_deg,
    elevation_m=BAD_HOMBURG.elevation_m,
    tz=BAD_HOMBURG.tz,
    horizon=HorizonProfile(points=[(0.0, 90.0)]),
)


def test_clears_horizon_respects_the_site_profile() -> None:
    from nachtlotse.engine import ephemeris

    low = ephemeris.AltAz(alt_deg=10.0, az_deg=180.0, distance_au=1.0)
    high = ephemeris.AltAz(alt_deg=80.0, az_deg=180.0, distance_au=1.0)

    assert constraints.clears_horizon(BAD_HOMBURG, low) is True  # flat horizon
    assert constraints.clears_horizon(WALLED_SITE, low) is False
    assert constraints.clears_horizon(WALLED_SITE, high) is False  # even near zenith


def test_best_time_tonight_is_none_behind_a_full_horizon_wall() -> None:
    """M2 DoD: a horizon that walls off the whole sky drops a target that
    the night/moon/altitude gate alone would have accepted.
    """
    reference = datetime(2026, 9, 12, 15, 0, tzinfo=UTC)

    assert (
        constraints.is_observable_tonight(
            BAD_HOMBURG, CIRCUMPOLAR_TARGET, reference, min_moon_sep_deg=0.0
        )
        is True
    )
    assert (
        constraints.best_time_tonight(
            WALLED_SITE, CIRCUMPOLAR_TARGET, reference, min_moon_sep_deg=0.0
        )
        is None
    )


def test_best_time_tonight_returns_a_horizon_clearing_position_when_open() -> None:
    reference = datetime(2026, 9, 12, 15, 0, tzinfo=UTC)

    result = constraints.best_time_tonight(
        BAD_HOMBURG, CIRCUMPOLAR_TARGET, reference, min_moon_sep_deg=0.0
    )

    assert result is not None
    _best_time, pos = result
    assert pos.alt_deg > 0.0
    assert constraints.clears_horizon(BAD_HOMBURG, pos) is True


# ERFA flags any UTC date past its leap-second table as a "dubious year" —
# expected here, since the date is deliberately far in the future.
@pytest.mark.filterwarnings("ignore::erfa.ErfaWarning")
def test_stale_iers_table_does_not_block_planning() -> None:
    """Regression: the bundled IERS table ages; astropy must not raise on it."""
    from astropy.utils import iers

    assert iers.conf.auto_download is False
    assert iers.conf.auto_max_age is None
    # UT1-UTC lookup for a date well beyond the bundled table's predictions.
    far_future = Time("2030-01-01T00:00:00", scale="utc")
    assert abs(far_future.ut1.jd - far_future.jd) < 1e-4


# --- per-night batching (performance) — must not change any result ---------

_NIGHT_REFERENCE = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def _astroplan_reference_observable(site: Site, target: Target, reference) -> bool:
    """The pre-check as it was originally written: astroplan's own
    `observability_table` with the three constraints, per target."""
    from astroplan import (
        AltitudeConstraint,
        AtNightConstraint,
        MoonSeparationConstraint,
        observability_table,
    )

    evening_start, morning_end = constraints.dark_window(site, reference)
    times = Time(
        np.linspace(
            Time(evening_start).jd,
            Time(morning_end).jd,
            constraints._SAMPLES_PER_NIGHT,
        ),
        format="jd",
    )
    table = observability_table(
        [
            AltitudeConstraint(min=constraints.DEFAULT_MIN_ALT_DEG * u.deg),
            AtNightConstraint.twilight_astronomical(),
            MoonSeparationConstraint(min=constraints.DEFAULT_MIN_MOON_SEP_DEG * u.deg),
        ],
        constraints.build_observer(site),
        [constraints.build_fixed_target(target)],
        times=times,
    )
    return bool(table["ever observable"][0])


def test_is_observable_tonight_matches_astroplans_observability_table() -> None:
    """The batched pre-check (Sun/Moon once per night) gives exactly the
    answer astroplan's per-target `observability_table` gives."""
    from nachtlotse.data.catalog import CATALOG

    sample = CATALOG[::12]  # ~20 real targets across the sky
    answers = [
        constraints.is_observable_tonight(BAD_HOMBURG, t, _NIGHT_REFERENCE)
        for t in sample
    ]
    assert any(answers) and not all(answers)  # a meaningful mix
    for target, answer in zip(sample, answers, strict=True):
        assert answer == _astroplan_reference_observable(
            BAD_HOMBURG, target, _NIGHT_REFERENCE
        ), target.catalog_id


def test_best_time_tonight_tries_extra_ok_highest_first_and_stops() -> None:
    """`extra_ok` is only consulted, highest candidate first, until one
    passes — and the answer is what a full scan would pick."""
    full = constraints.best_time_tonight(
        BAD_HOMBURG, CIRCUMPOLAR_TARGET, _NIGHT_REFERENCE, min_moon_sep_deg=0.0
    )
    assert full is not None
    asked: list[float] = []

    def reject_the_peak(when: datetime, pos) -> bool:
        asked.append(pos.alt_deg)
        return when != full[0]

    second = constraints.best_time_tonight(
        BAD_HOMBURG,
        CIRCUMPOLAR_TARGET,
        _NIGHT_REFERENCE,
        min_moon_sep_deg=0.0,
        extra_ok=reject_the_peak,
    )
    assert second is not None
    assert len(asked) == 2  # the peak (rejected), then the runner-up
    assert asked[0] == full[1].alt_deg
    assert second[1].alt_deg == asked[1] <= full[1].alt_deg


# --- nights without astronomical darkness (midsummer) ---------------------

_MIDSUMMER = datetime(2026, 6, 21, 10, 0, tzinfo=UTC)


def _sun_alt_deg(site: Site, when: datetime) -> float:
    from astropy.coordinates import AltAz, get_sun

    frame = AltAz(obstime=Time(when), location=constraints._earth_location(site))
    return float(get_sun(Time(when)).transform_to(frame).alt.deg)


def test_dark_window_is_astronomical_on_an_ordinary_night() -> None:
    reference = datetime(2026, 10, 4, 10, 0, tzinfo=UTC)
    start, end = constraints.dark_window(BAD_HOMBURG, reference)
    assert constraints.darkness(BAD_HOMBURG, reference) == "astronomical"
    assert _sun_alt_deg(BAD_HOMBURG, start) == pytest.approx(-18.0, abs=0.1)
    assert _sun_alt_deg(BAD_HOMBURG, end) == pytest.approx(-18.0, abs=0.1)


def test_dark_window_falls_back_to_nautical_at_midsummer() -> None:
    """At 50°N the Sun never gets below -18° around the solstice — this
    used to crash with a TypeError (astroplan's masked "no crossing")."""
    start, end = constraints.dark_window(BAD_HOMBURG, _MIDSUMMER)
    assert constraints.darkness(BAD_HOMBURG, _MIDSUMMER) == "nautical"
    assert _sun_alt_deg(BAD_HOMBURG, start) == pytest.approx(-12.0, abs=0.1)
    assert _sun_alt_deg(BAD_HOMBURG, end) == pytest.approx(-12.0, abs=0.1)
    # Never astronomically dark in between: the deepest point stays above -18°.
    midpoint = start + (end - start) / 2
    assert -18.0 < _sun_alt_deg(BAD_HOMBURG, midpoint) < -12.0
    # That night's evening, not some other night's.
    assert start.date() == _MIDSUMMER.date()
    assert timedelta(hours=2) < end - start < timedelta(hours=6)


def test_dark_window_keeps_short_astronomical_nights_at_the_season_edges() -> None:
    reference = datetime(2026, 7, 14, 10, 0, tzinfo=UTC)
    start, end = constraints.dark_window(BAD_HOMBURG, reference)
    assert constraints.darkness(BAD_HOMBURG, reference) == "astronomical"
    assert end - start < timedelta(hours=2)


def test_dark_window_raises_no_dark_window_far_north_at_midsummer() -> None:
    far_north = Site(
        name="Far north",
        lat_deg=65.0,
        lon_deg=20.0,
        elevation_m=0.0,
        tz="Europe/Stockholm",
        horizon=HorizonProfile(points=[]),
    )
    with pytest.raises(constraints.NoDarkWindow, match="Sun doesn't get below -12°"):
        constraints.dark_window(far_north, _MIDSUMMER)


def test_targets_are_still_found_in_a_nautical_night() -> None:
    result = constraints.best_time_tonight(
        BAD_HOMBURG, CIRCUMPOLAR_TARGET, _MIDSUMMER, min_moon_sep_deg=0.0
    )
    assert result is not None
    start, end = constraints.dark_window(BAD_HOMBURG, _MIDSUMMER)
    assert start <= result[0] <= end

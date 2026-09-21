"""Ephemeris tests against independently known values (M0 DoD).

No comparison of the engine against itself: the expected values come from
textbook astronomy (Polaris altitude ~ site latitude; transit altitude =
90° - lat + dec), not from skyfield output.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from itertools import pairwise

import pytest

from nachtlotse.engine import ephemeris
from nachtlotse.engine.models import HorizonProfile, Site, Target

BAD_HOMBURG = Site(
    name="Bad Homburg",
    lat_deg=50.2266,
    lon_deg=8.6180,
    elevation_m=190.0,
    tz="Europe/Berlin",
    horizon=HorizonProfile(points=[]),
)

POLARIS = Target(
    name="Polaris", ra_deg=37.9546, dec_deg=89.2641, catalog_id="alpha UMi"
)
M31 = Target(name="Andromeda Galaxy", ra_deg=10.6847, dec_deg=41.2687, catalog_id="M31")


def test_polaris_altitude_matches_site_latitude_approximately() -> None:
    """Polaris sits (almost) at the celestial north pole -> altitude ~= site latitude."""
    when = datetime(2026, 9, 12, 22, 0, tzinfo=UTC)
    pos = ephemeris.altaz(BAD_HOMBURG, POLARIS, when)

    assert pos.alt_deg == pytest.approx(BAD_HOMBURG.lat_deg, abs=1.0)
    assert pos.az_deg < 5.0 or pos.az_deg > 355.0


def test_m31_transit_is_due_south_at_meridian_altitude() -> None:
    """Upper culmination: azimuth 180° (south), altitude = 90° - lat + dec."""
    start = datetime(2026, 9, 12, 0, 0, tzinfo=UTC)
    end = start + timedelta(days=1)

    transit_time = ephemeris.find_transit(BAD_HOMBURG, M31, start, end)
    pos = ephemeris.altaz(BAD_HOMBURG, M31, transit_time)

    expected_alt_deg = 90.0 - BAD_HOMBURG.lat_deg + M31.dec_deg
    assert pos.alt_deg == pytest.approx(expected_alt_deg, abs=0.5)
    assert pos.az_deg == pytest.approx(180.0, abs=0.5)


def test_altitude_rises_toward_transit_and_falls_afterward() -> None:
    """Rough sanity check: lower an hour before/after transit than at transit."""
    start = datetime(2026, 9, 12, 0, 0, tzinfo=UTC)
    end = start + timedelta(days=1)

    transit_time = ephemeris.find_transit(BAD_HOMBURG, M31, start, end)
    alt_at_transit = ephemeris.altaz(BAD_HOMBURG, M31, transit_time).alt_deg
    alt_one_hour_before = ephemeris.altaz(
        BAD_HOMBURG, M31, transit_time - timedelta(hours=1)
    ).alt_deg
    alt_one_hour_after = ephemeris.altaz(
        BAD_HOMBURG, M31, transit_time + timedelta(hours=1)
    ).alt_deg

    assert alt_at_transit > alt_one_hour_before
    assert alt_at_transit > alt_one_hour_after


def test_max_altitude_matches_transit_when_window_contains_it() -> None:
    start = datetime(2026, 9, 12, 0, 0, tzinfo=UTC)
    end = start + timedelta(days=1)

    transit_time = ephemeris.find_transit(BAD_HOMBURG, M31, start, end)
    max_time, max_pos = ephemeris.max_altitude(BAD_HOMBURG, M31, start, end)

    assert max_time == transit_time
    assert max_pos == ephemeris.altaz(BAD_HOMBURG, M31, transit_time)


def test_max_altitude_falls_back_to_window_edge_when_transit_is_excluded() -> None:
    day_start = datetime(2026, 9, 12, 0, 0, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)
    transit_time = ephemeris.find_transit(BAD_HOMBURG, M31, day_start, day_end)
    transit_alt_deg = ephemeris.altaz(BAD_HOMBURG, M31, transit_time).alt_deg

    # A short window entirely after the transit: altitude only falls across
    # it, so the maximum must sit at its start edge.
    window_start = transit_time + timedelta(hours=1)
    window_end = transit_time + timedelta(hours=2)

    with pytest.raises(ValueError, match="No culmination"):
        ephemeris.find_transit(BAD_HOMBURG, M31, window_start, window_end)

    max_time, max_pos = ephemeris.max_altitude(
        BAD_HOMBURG, M31, window_start, window_end
    )

    assert max_time == window_start
    assert max_pos == ephemeris.altaz(BAD_HOMBURG, M31, window_start)
    assert max_pos.alt_deg < transit_alt_deg


def test_altitude_series_matches_transit_altitude_and_spans_the_window() -> None:
    start = datetime(2026, 9, 12, 0, 0, tzinfo=UTC)
    end = start + timedelta(days=1)
    transit_time = ephemeris.find_transit(BAD_HOMBURG, M31, start, end)
    expected_transit_alt_deg = ephemeris.altaz(BAD_HOMBURG, M31, transit_time).alt_deg

    series = ephemeris.altitude_series(BAD_HOMBURG, M31, start, end, num_samples=49)

    assert len(series) == 49
    assert series[0][0].timestamp() == pytest.approx(start.timestamp(), abs=1.0), (
        "first sample should sit at the window start"
    )
    assert series[-1][0].timestamp() == pytest.approx(end.timestamp(), abs=1.0), (
        "last sample should sit at the window end"
    )
    sample_alts = [pos.alt_deg for _when, pos in series]
    assert max(sample_alts) == pytest.approx(expected_transit_alt_deg, abs=0.5)


def test_altaz_requires_timezone_aware_datetime() -> None:
    naive = datetime(2026, 9, 12, 22, 0)  # noqa: DTZ001 -- test case for the guard
    with pytest.raises(ValueError):
        ephemeris.altaz(BAD_HOMBURG, POLARIS, naive)


def test_moon_altaz_series_spans_the_window_with_plausible_positions() -> None:
    start = datetime(2026, 9, 12, 20, 0, tzinfo=UTC)
    end = start + timedelta(hours=8)

    series = ephemeris.moon_altaz_series(BAD_HOMBURG, start, end, num_samples=17)

    assert len(series) == 17
    assert series[0][0].timestamp() == pytest.approx(start.timestamp(), abs=1.0)
    assert series[-1][0].timestamp() == pytest.approx(end.timestamp(), abs=1.0)
    for _when, pos in series:
        assert -90.0 <= pos.alt_deg <= 90.0
        assert 0.0 <= pos.az_deg < 360.0
    # The Moon is close enough that geocentric vs. topocentric distance
    # differs measurably (unlike the "infinitely far" catalog stars) —
    # a sanity check that this is really observing the Moon body, not
    # accidentally reusing the fixed-star code path.
    assert all(0.0022 < pos.distance_au < 0.0028 for _when, pos in series)


def test_moon_rise_set_events_alternate_and_fall_within_the_window() -> None:
    start = datetime(2026, 9, 12, 0, 0, tzinfo=UTC)
    end = start + timedelta(days=3)

    events = ephemeris.moon_rise_set_events(BAD_HOMBURG, start, end)

    assert len(events) >= 4, "3 days should contain several rise/set events"
    for when, _is_rising in events:
        assert start <= when <= end
    # Rise/set alternate strictly (a rise is always followed by a set and
    # vice versa) — the Moon can't rise twice without setting in between.
    risings = [is_rising for _when, is_rising in events]
    for is_rising, next_is_rising in pairwise(risings):
        assert is_rising != next_is_rising


def test_moon_rise_set_events_empty_when_moon_never_crosses_the_horizon() -> None:
    # The Moon set at 17:53 UTC on 2026-09-12 and doesn't rise again until
    # 07:49 UTC the next day (see the 3-day sweep above) — this window
    # sits entirely inside that down period.
    start = datetime(2026, 9, 12, 19, 0, tzinfo=UTC)
    end = datetime(2026, 9, 13, 5, 0, tzinfo=UTC)

    assert ephemeris.moon_rise_set_events(BAD_HOMBURG, start, end) == []


def test_moon_phase_angle_matches_astroplans_illumination_fraction() -> None:
    """Cross-checked against an independent library (astroplan), not
    against this engine's own output — same policy `test_ephemeris.py`'s
    module docstring states for every other value in this file.

    `moon_phase_angle_deg` (0° new, 180° full) implies an illuminated
    fraction of (1 - cos(angle)) / 2; astroplan's `moon_illumination`
    computes that fraction its own way. They should closely agree
    regardless of date (new moon, full moon, or in between).
    """
    from astroplan import moon_illumination
    from astropy.time import Time

    for when in (
        datetime(2026, 9, 12, 22, 0, tzinfo=UTC),  # near new moon
        datetime(2026, 9, 26, 3, 0, tzinfo=UTC),  # near full moon
        datetime(2026, 10, 5, 1, 0, tzinfo=UTC),  # in between
    ):
        angle_deg = ephemeris.moon_phase_angle_deg(when)
        assert 0.0 <= angle_deg < 360.0

        implied_fraction = (1 - math.cos(math.radians(angle_deg))) / 2
        expected_fraction = float(moon_illumination(Time(when)))
        assert implied_fraction == pytest.approx(expected_fraction, abs=0.02)

"""Ephemeris tests against independently known values (M0 DoD).

No comparison of the engine against itself: the expected values come from
textbook astronomy (Polaris altitude ~ site latitude; transit altitude =
90° - lat + dec), not from skyfield output.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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

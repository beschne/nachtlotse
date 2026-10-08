"""Tests for the night verdict (nachtlotse/engine/night.py) against values
worked out by hand from the hourly forecast."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from nachtlotse.engine import night
from nachtlotse.engine.models import HourlyConditions

DAY = datetime(2026, 10, 8, tzinfo=UTC)


def at(hour: int, minute: int = 0) -> datetime:
    """`hour` o'clock on the evening of DAY, hours past 24 roll into the
    next morning."""
    return DAY + timedelta(hours=hour, minutes=minute)


def forecast(
    first_hour: int,
    cloud_pct: list[float],
    wind_kmh: float = 5.0,
    dew_spread_c: float = 6.0,
) -> list[HourlyConditions]:
    return [
        HourlyConditions(at(first_hour + i), cloud, wind_kmh, dew_spread_c)
        for i, cloud in enumerate(cloud_pct)
    ]


def verdict(hours, start, end, moon_pct=0.0, moon_up_h=0.0):
    return night.night_verdict(
        hours, start, end, moon_illumination_pct=moon_pct, moon_up_h=moon_up_h
    )


def test_a_fully_clear_window_is_one_run_and_a_go() -> None:
    result = verdict(forecast(21, [0] * 8), at(21, 30), at(27, 10))
    assert result.level == "GO"
    assert result.longest_run is not None
    assert result.longest_run.start == at(21, 30)
    assert result.longest_run.end == at(27, 10)
    # 21:30 to 03:10 is 5 h 40 min.
    assert result.longest_run.duration_h == pytest.approx(5 + 40 / 60)
    assert result.window_h == pytest.approx(5 + 40 / 60)
    assert result.clear_h == pytest.approx(result.window_h)
    assert result.held_back_by == ()


def test_a_cloudy_hour_splits_the_night_and_the_longest_run_decides() -> None:
    # 22-01 clear (3 h), 01-02 cloudy, 02-04 clear (2 h).
    result = verdict(forecast(22, [0, 10, 20, 90, 0, 0]), at(22), at(28))
    assert result.longest_run is not None
    assert (result.longest_run.start, result.longest_run.end) == (at(22), at(25))
    assert result.longest_run.duration_h == pytest.approx(3.0)
    assert result.clear_h == pytest.approx(5.0)
    assert result.level == "GO"  # exactly the 3 h GO needs


def test_an_average_of_forty_percent_can_still_be_a_skip() -> None:
    # Alternating clear and closed hours: the night averages below 40%
    # cloud, yet no clear stretch lasts longer than an hour.
    clouds = [0, 70, 0, 70, 0, 70, 0, 70]  # mean 35%
    result = verdict(forecast(21, clouds), at(21), at(29))
    assert sum(clouds) / len(clouds) < 40
    assert result.longest_run is not None
    assert result.longest_run.duration_h == pytest.approx(1.0)
    assert result.level == "SKIP"


@pytest.mark.parametrize(
    ("clear_hours", "expected"), [(1, "SKIP"), (2, "MARGINAL"), (3, "GO"), (5, "GO")]
)
def test_levels_at_whole_hour_run_lengths(clear_hours: int, expected: str) -> None:
    clouds = [0.0] * clear_hours + [100.0] * (8 - clear_hours)
    assert verdict(forecast(21, clouds), at(21), at(29)).level == expected


@pytest.mark.parametrize(("start_minute", "expected"), [(30, "MARGINAL"), (40, "SKIP")])
def test_levels_either_side_of_one_and_a_half_hours(
    start_minute: int, expected: str
) -> None:
    # Clear 21:xx-23:00 only: 1 h 30 min from 21:30, 1 h 20 min from 21:40.
    hours = forecast(21, [0.0, 0.0] + [100.0] * 6)
    assert verdict(hours, at(21, start_minute), at(29)).level == expected


def test_forty_percent_cloud_is_not_clear() -> None:
    assert night.clear_runs(forecast(21, [39.9]), at(21), at(22))
    assert not night.clear_runs(forecast(21, [40.0]), at(21), at(22))


def test_hours_are_clipped_to_the_dark_window() -> None:
    # The 21:00 forecast hour only counts from 21:30 on, the 23:00 hour
    # only until 23:15.
    runs = night.clear_runs(forecast(21, [0, 0, 0]), at(21, 30), at(23, 15))
    assert [(r.start, r.end) for r in runs] == [(at(21, 30), at(23, 15))]


def test_a_gap_in_the_forecast_breaks_a_run_and_is_not_clear() -> None:
    hours = forecast(21, [0, 0]) + forecast(24, [0, 0])  # nothing for 23-24
    runs = night.clear_runs(hours, at(21), at(26))
    assert [(r.start, r.end) for r in runs] == [(at(21), at(23)), (at(24), at(26))]


def test_no_forecast_gives_no_level() -> None:
    result = verdict([], at(21), at(29))
    assert result.level is None
    assert result.longest_run is None
    assert result.forecast_h == 0.0
    assert result.window_h == pytest.approx(8.0)


def test_a_forecast_ending_before_the_window_gives_no_level() -> None:
    result = verdict(forecast(10, [0] * 4), at(21), at(29))
    assert result.level is None


def test_partial_coverage_cannot_rule_out_a_skip_but_can_confirm_a_go() -> None:
    # Forecast covers 21-24 of a 21-29 window.
    cloudy = verdict(forecast(21, [100, 100, 100]), at(21), at(29))
    assert cloudy.forecast_h == pytest.approx(3.0)
    assert cloudy.level is None
    clear = verdict(forecast(21, [0, 0, 0]), at(21), at(29))
    assert clear.level == "GO"


def test_held_back_by_lists_only_costs_biggest_first() -> None:
    hours = (
        forecast(21, [0, 0, 0, 0], wind_kmh=30.0, dew_spread_c=1.0)  # 4 h wind+dew
        + forecast(25, [100, 100], wind_kmh=5.0, dew_spread_c=6.0)  # 2 h cloud
        + forecast(27, [0, 0], wind_kmh=5.0, dew_spread_c=6.0)
    )
    result = verdict(hours, at(21), at(29), moon_pct=98.0, moon_up_h=3.5)
    assert [item.term for item in result.held_back_by] == [
        "wind",
        "dew",
        "moon",
        "cloud",
    ]
    by_term = {item.term: item for item in result.held_back_by}
    assert by_term["wind"].duration_h == pytest.approx(4.0)
    assert by_term["cloud"].duration_h == pytest.approx(2.0)
    assert by_term["moon"].detail == "Moon 98% illuminated, up for 3.5 h"
    assert by_term["wind"].detail == "wind of 25 km/h or more for 4.0 h"


def test_a_thin_moon_or_a_moon_that_is_down_is_not_a_cost() -> None:
    hours = forecast(21, [0] * 8)
    assert (
        verdict(hours, at(21), at(29), moon_pct=20.0, moon_up_h=6.0).held_back_by == ()
    )
    assert (
        verdict(hours, at(21), at(29), moon_pct=98.0, moon_up_h=0.0).held_back_by == ()
    )


@pytest.mark.parametrize(
    ("total", "low", "mid", "high", "expected"),
    [
        (70.0, 0.0, 0.0, 70.0, 35.0),  # cirrus only: half weight
        (100.0, 0.0, 0.0, 100.0, 50.0),
        (60.0, 60.0, 10.0, 90.0, 60.0),  # low cloud counts in full
        (60.0, 10.0, 55.0, 20.0, 55.0),  # so does mid cloud
        (30.0, 0.0, 0.0, 90.0, 30.0),  # never above the total
        (70.0, None, 0.0, 70.0, 70.0),  # a missing layer: the total stands
        (70.0, 0.0, 0.0, None, 70.0),
    ],
)
def test_thin_high_cloud_counts_at_half_weight(
    total: float, low, mid, high, expected: float
) -> None:
    assert night.effective_cloud_cover_pct(total, low, mid, high) == pytest.approx(
        expected
    )


def test_cloud_at_finds_the_forecast_hour_containing_a_moment() -> None:
    hours = forecast(21, [10, 50, 90])
    assert night.cloud_at(hours, at(21)) == 10
    assert night.cloud_at(hours, at(22, 59)) == 50
    assert night.cloud_at(hours, at(23, 30)) == 90
    assert night.cloud_at(hours, at(24)) is None  # one past the last hour
    assert night.cloud_at(hours, at(20, 59)) is None  # before the first

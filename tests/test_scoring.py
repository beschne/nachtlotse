"""Verdict-heuristic tests (M4 DoD): overcast -> SKIP with a stated reason;
a clear window with a low target -> MARGINAL."""

from __future__ import annotations

import pytest

from nachtlotse.engine import scoring
from nachtlotse.engine.models import WeatherSummary

CLEAR_CALM_WEATHER = WeatherSummary(
    max_cloud_cover_pct=10.0,
    avg_cloud_cover_pct=5.0,
    max_wind_kmh=10.0,
    min_dew_point_spread_c=5.0,
)

OVERCAST_WEATHER = WeatherSummary(
    max_cloud_cover_pct=95.0,
    avg_cloud_cover_pct=80.0,
    max_wind_kmh=10.0,
    min_dew_point_spread_c=5.0,
)


def test_overcast_sky_is_skip_with_cloud_cover_named_as_the_reason() -> None:
    verdict = scoring.verdict_for_target(70.0, weather=OVERCAST_WEATHER)

    assert verdict.level == "SKIP"
    assert any("cloud" in reason.lower() for reason in verdict.reasons)
    assert any("95" in reason for reason in verdict.reasons)


def test_clear_window_with_a_low_target_is_marginal() -> None:
    low_alt_deg = scoring.MARGINAL_ALTITUDE_DEG - 5.0
    verdict = scoring.verdict_for_target(low_alt_deg, weather=CLEAR_CALM_WEATHER)

    assert verdict.level == "MARGINAL"
    assert any("altitude" in reason.lower() for reason in verdict.reasons)


def test_clear_window_with_a_high_target_is_go() -> None:
    high_alt_deg = scoring.MARGINAL_ALTITUDE_DEG + 30.0
    verdict = scoring.verdict_for_target(high_alt_deg, weather=CLEAR_CALM_WEATHER)

    assert verdict.level == "GO"
    assert verdict.reasons  # always explains itself, even when everything is fine


def test_missing_weather_caps_the_verdict_at_marginal_even_for_a_high_target() -> None:
    """Without a forecast we can't rule out clouds/wind/dew, so this must
    never claim GO — an unconfirmed sky is a real uncertainty, not a
    "clear until proven otherwise" default.
    """
    high_alt_deg = scoring.MARGINAL_ALTITUDE_DEG + 30.0
    verdict = scoring.verdict_for_target(high_alt_deg, weather=None)

    assert verdict.level == "MARGINAL"
    assert any("weather" in reason.lower() for reason in verdict.reasons)


def test_missing_weather_does_not_prevent_a_low_altitude_marginal() -> None:
    low_alt_deg = scoring.MARGINAL_ALTITUDE_DEG - 5.0
    verdict = scoring.verdict_for_target(low_alt_deg, weather=None)

    assert verdict.level == "MARGINAL"


@pytest.mark.parametrize(
    "max_wind_kmh,expected_level",
    [
        (scoring.SKIP_WIND_KMH + 1.0, "SKIP"),
        (scoring.MARGINAL_WIND_KMH + 1.0, "MARGINAL"),
    ],
)
def test_high_wind_downgrades_the_verdict(
    max_wind_kmh: float, expected_level: str
) -> None:
    weather = WeatherSummary(
        max_cloud_cover_pct=5.0,
        avg_cloud_cover_pct=5.0,
        max_wind_kmh=max_wind_kmh,
        min_dew_point_spread_c=5.0,
    )
    verdict = scoring.verdict_for_target(70.0, weather=weather)

    assert verdict.level == expected_level
    assert any("wind" in reason.lower() for reason in verdict.reasons)


def test_dew_risk_downgrades_to_marginal() -> None:
    weather = WeatherSummary(
        max_cloud_cover_pct=5.0,
        avg_cloud_cover_pct=5.0,
        max_wind_kmh=5.0,
        min_dew_point_spread_c=scoring.MARGINAL_DEW_POINT_SPREAD_C - 0.5,
    )
    verdict = scoring.verdict_for_target(70.0, weather=weather)

    assert verdict.level == "MARGINAL"
    assert any("dew" in reason.lower() for reason in verdict.reasons)


def test_skip_outranks_marginal_even_when_both_apply() -> None:
    weather = WeatherSummary(
        max_cloud_cover_pct=scoring.SKIP_CLOUD_COVER_PCT + 1.0,
        avg_cloud_cover_pct=scoring.SKIP_CLOUD_COVER_PCT,
        max_wind_kmh=5.0,
        min_dew_point_spread_c=5.0,
    )
    low_alt_deg = scoring.MARGINAL_ALTITUDE_DEG - 5.0  # would be MARGINAL on its own
    verdict = scoring.verdict_for_target(low_alt_deg, weather=weather)

    assert verdict.level == "SKIP"
    assert len(verdict.reasons) >= 2  # both the cloud and the altitude reason survive


def test_a_nautical_only_night_caps_the_verdict_at_marginal() -> None:
    clear = WeatherSummary(
        max_cloud_cover_pct=5.0,
        avg_cloud_cover_pct=2.0,
        max_wind_kmh=5.0,
        min_dew_point_spread_c=8.0,
    )
    assert scoring.verdict_for_target(70.0, weather=clear).level == "GO"
    verdict = scoring.verdict_for_target(70.0, weather=clear, darkness="nautical")
    assert verdict.level == "MARGINAL"
    assert any("no astronomical darkness" in r for r in verdict.reasons)


_CLOUDY_NIGHT = WeatherSummary(
    max_cloud_cover_pct=70.0,
    avg_cloud_cover_pct=30.0,
    max_wind_kmh=5.0,
    min_dew_point_spread_c=6.0,
)
_CLEAR_NIGHT = WeatherSummary(
    max_cloud_cover_pct=10.0,
    avg_cloud_cover_pct=5.0,
    max_wind_kmh=5.0,
    min_dew_point_spread_c=6.0,
)


def test_a_best_time_in_a_cloudy_hour_is_named_as_a_reason() -> None:
    verdict = scoring.verdict_for_target(
        70.0, weather=_CLOUDY_NIGHT, cloud_at_best_time_pct=65.0
    )
    assert verdict.level == "MARGINAL"
    assert "best time falls in a cloudy hour (65% effective cloud)" in verdict.reasons


def test_a_best_time_in_a_clear_hour_adds_a_note_but_keeps_the_level() -> None:
    without = scoring.verdict_for_target(70.0, weather=_CLOUDY_NIGHT)
    verdict = scoring.verdict_for_target(
        70.0, weather=_CLOUDY_NIGHT, cloud_at_best_time_pct=10.0
    )
    assert verdict.level == without.level == "MARGINAL"  # the window's worst hour
    assert "best time falls in a clear hour (10% effective cloud)" in verdict.reasons


def test_a_clear_night_gets_no_best_time_cloud_reason() -> None:
    verdict = scoring.verdict_for_target(
        70.0, weather=_CLEAR_NIGHT, cloud_at_best_time_pct=10.0
    )
    assert verdict.level == "GO"
    assert not any("best time" in reason for reason in verdict.reasons)


def test_best_time_cloud_is_ignored_without_a_forecast_or_without_its_hour() -> None:
    no_weather = scoring.verdict_for_target(70.0, cloud_at_best_time_pct=90.0)
    assert not any("best time" in reason for reason in no_weather.reasons)
    no_hour = scoring.verdict_for_target(
        70.0, weather=_CLOUDY_NIGHT, cloud_at_best_time_pct=None
    )
    assert not any("best time" in reason for reason in no_hour.reasons)

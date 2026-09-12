"""Open-Meteo client tests — network is always mocked here; the test suite
must stay offline-safe (see CLAUDE.md's Leitprinzip)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from nachtlotse.weather import open_meteo

_SAMPLE_PAYLOAD = {
    "hourly": {
        "time": ["2026-09-12T20:00", "2026-09-12T21:00", "2026-09-12T22:00"],
        "cloudcover": [10.0, 40.0, 90.0],
        "windspeed_10m": [5.0, 8.0, 12.0],
        "relative_humidity_2m": [60.0, 65.0, 70.0],
        "dew_point_2m": [8.0, 7.5, 7.0],
        "temperature_2m": [15.0, 13.0, 11.0],
    }
}


def _mock_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


def test_fetch_hourly_parses_a_well_formed_response() -> None:
    with patch("urllib.request.urlopen", return_value=_mock_response(_SAMPLE_PAYLOAD)):
        hours = open_meteo.fetch_hourly(50.237, 8.551)

    assert len(hours) == 3
    assert hours[0].when == datetime(2026, 9, 12, 20, 0, tzinfo=UTC)
    assert hours[0].cloud_cover_pct == pytest.approx(10.0)
    assert hours[2].cloud_cover_pct == pytest.approx(90.0)
    assert hours[1].wind_speed_kmh == pytest.approx(8.0)
    assert hours[1].dew_point_c == pytest.approx(7.5)


def test_fetch_hourly_requests_a_forecast_horizon_of_at_least_two_weeks() -> None:
    """Regression guard: `lotse plan --date` needs weather for any night
    within a couple of weeks out, not just tonight — a too-short
    `forecast_days` silently degrades every future-dated query to
    "Weather: unavailable" without ever raising an error.
    """
    with patch(
        "urllib.request.urlopen", return_value=_mock_response(_SAMPLE_PAYLOAD)
    ) as mock_urlopen:
        open_meteo.fetch_hourly(50.237, 8.551)

    requested_url = mock_urlopen.call_args.args[0]
    query = urllib.parse.parse_qs(urllib.parse.urlparse(requested_url).query)
    assert int(query["forecast_days"][0]) >= 14


def test_fetch_hourly_raises_weather_unavailable_on_network_error() -> None:
    with (
        patch(
            "urllib.request.urlopen", side_effect=urllib.error.URLError("no network")
        ),
        pytest.raises(open_meteo.WeatherUnavailable),
    ):
        open_meteo.fetch_hourly(50.237, 8.551)


def test_fetch_hourly_raises_weather_unavailable_on_invalid_json() -> None:
    response = MagicMock()
    response.read.return_value = b"not json"
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    with (
        patch("urllib.request.urlopen", return_value=response),
        pytest.raises(open_meteo.WeatherUnavailable),
    ):
        open_meteo.fetch_hourly(50.237, 8.551)


def test_fetch_hourly_raises_weather_unavailable_on_missing_field() -> None:
    incomplete_payload = {
        "hourly": {"time": ["2026-09-12T20:00"]}
    }  # no cloudcover etc.
    with (
        patch(
            "urllib.request.urlopen", return_value=_mock_response(incomplete_payload)
        ),
        pytest.raises(open_meteo.WeatherUnavailable),
    ):
        open_meteo.fetch_hourly(50.237, 8.551)


def test_summarize_window_aggregates_only_hours_inside_the_window() -> None:
    with patch("urllib.request.urlopen", return_value=_mock_response(_SAMPLE_PAYLOAD)):
        hours = open_meteo.fetch_hourly(50.237, 8.551)

    # Window covers only the last two hours (21:00, 22:00).
    start = datetime(2026, 9, 12, 21, 0, tzinfo=UTC)
    end = datetime(2026, 9, 12, 22, 0, tzinfo=UTC)
    summary = open_meteo.summarize_window(hours, start, end)

    assert summary is not None
    assert summary.max_cloud_cover_pct == pytest.approx(90.0)
    assert summary.avg_cloud_cover_pct == pytest.approx((40.0 + 90.0) / 2)
    assert summary.max_wind_kmh == pytest.approx(12.0)
    assert summary.min_dew_point_spread_c == pytest.approx(min(13.0 - 7.5, 11.0 - 7.0))


def test_summarize_window_returns_none_when_window_is_outside_the_forecast() -> None:
    with patch("urllib.request.urlopen", return_value=_mock_response(_SAMPLE_PAYLOAD)):
        hours = open_meteo.fetch_hourly(50.237, 8.551)

    far_future_start = datetime(2030, 1, 1, 0, 0, tzinfo=UTC)
    far_future_end = datetime(2030, 1, 1, 6, 0, tzinfo=UTC)
    assert open_meteo.summarize_window(hours, far_future_start, far_future_end) is None

"""Open-Meteo client tests — network is always mocked here; the test suite
must stay offline-safe (see CLAUDE.md's Leitprinzip)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
from datetime import UTC, datetime, timedelta
from pathlib import Path
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


def test_fetch_hourly_drops_trailing_null_hours_instead_of_failing_entirely() -> None:
    """Regression test: Open-Meteo's 16-day hourly forecast leaves a
    handful of hours at the far edge of the horizon `null` across every
    field. A single `float(None)` there must not discard the whole
    fetch — tonight's hours are still perfectly valid.
    """
    payload_with_trailing_nulls = {
        "hourly": {
            "time": [
                "2026-09-12T20:00",
                "2026-09-12T21:00",
                "2026-09-12T22:00",
            ],
            "cloudcover": [10.0, 40.0, None],
            "windspeed_10m": [5.0, 8.0, None],
            "relative_humidity_2m": [60.0, 65.0, None],
            "dew_point_2m": [8.0, 7.5, None],
            "temperature_2m": [15.0, 13.0, None],
        }
    }
    with patch(
        "urllib.request.urlopen",
        return_value=_mock_response(payload_with_trailing_nulls),
    ):
        hours = open_meteo.fetch_hourly(50.237, 8.551)

    assert len(hours) == 2
    assert hours[0].when == datetime(2026, 9, 12, 20, 0, tzinfo=UTC)
    assert hours[1].when == datetime(2026, 9, 12, 21, 0, tzinfo=UTC)


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


def test_hourly_forecast_in_window_keeps_each_hour_instead_of_aggregating() -> None:
    with patch("urllib.request.urlopen", return_value=_mock_response(_SAMPLE_PAYLOAD)):
        hours = open_meteo.fetch_hourly(50.237, 8.551)

    start = datetime(2026, 9, 12, 21, 0, tzinfo=UTC)
    end = datetime(2026, 9, 12, 22, 0, tzinfo=UTC)
    in_window = open_meteo.hourly_forecast_in_window(hours, start, end)

    assert [hour.cloud_cover_pct for hour in in_window] == [40.0, 90.0]
    assert all(start <= hour.when <= end for hour in in_window)


def test_hourly_forecast_in_window_empty_outside_the_forecast() -> None:
    with patch("urllib.request.urlopen", return_value=_mock_response(_SAMPLE_PAYLOAD)):
        hours = open_meteo.fetch_hourly(50.237, 8.551)

    far_future_start = datetime(2030, 1, 1, 0, 0, tzinfo=UTC)
    far_future_end = datetime(2030, 1, 1, 6, 0, tzinfo=UTC)
    assert open_meteo.hourly_forecast_in_window(hours, far_future_start, far_future_end) == []


def test_fetch_hourly_cached_serves_a_fresh_cache_entry_without_a_network_call(
    tmp_path: Path,
) -> None:
    with patch(
        "urllib.request.urlopen", return_value=_mock_response(_SAMPLE_PAYLOAD)
    ) as mock_urlopen:
        first = open_meteo.fetch_hourly_cached(50.237, 8.551, cache_dir=tmp_path)
        second = open_meteo.fetch_hourly_cached(50.237, 8.551, cache_dir=tmp_path)

    assert mock_urlopen.call_count == 1
    assert second == first


def test_fetch_hourly_cached_refetches_once_the_cache_entry_expires(
    tmp_path: Path,
) -> None:
    with patch("urllib.request.urlopen", return_value=_mock_response(_SAMPLE_PAYLOAD)):
        open_meteo.fetch_hourly_cached(50.237, 8.551, cache_dir=tmp_path)

    cache_file = next(tmp_path.iterdir())
    payload = json.loads(cache_file.read_text())
    stale_fetched_at = datetime.now(UTC) - timedelta(
        hours=open_meteo.CACHE_TTL_HOURS, minutes=1
    )
    payload["fetched_at"] = stale_fetched_at.isoformat()
    cache_file.write_text(json.dumps(payload))

    with patch(
        "urllib.request.urlopen", return_value=_mock_response(_SAMPLE_PAYLOAD)
    ) as mock_urlopen:
        open_meteo.fetch_hourly_cached(50.237, 8.551, cache_dir=tmp_path)

    assert mock_urlopen.call_count == 1


def test_fetch_hourly_cached_treats_a_corrupt_cache_file_as_a_miss(
    tmp_path: Path,
) -> None:
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "50.237_8.551.json").write_text("not json")

    with patch(
        "urllib.request.urlopen", return_value=_mock_response(_SAMPLE_PAYLOAD)
    ) as mock_urlopen:
        hours = open_meteo.fetch_hourly_cached(50.237, 8.551, cache_dir=tmp_path)

    assert mock_urlopen.call_count == 1
    assert len(hours) == 3


def test_fetch_hourly_cached_keys_the_cache_by_coordinates(tmp_path: Path) -> None:
    with patch(
        "urllib.request.urlopen", return_value=_mock_response(_SAMPLE_PAYLOAD)
    ) as mock_urlopen:
        open_meteo.fetch_hourly_cached(50.237, 8.551, cache_dir=tmp_path)
        open_meteo.fetch_hourly_cached(48.137, 11.575, cache_dir=tmp_path)

    assert mock_urlopen.call_count == 2
    assert len(list(tmp_path.iterdir())) == 2

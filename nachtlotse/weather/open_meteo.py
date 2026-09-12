"""Open-Meteo weather client — the one place in this project that makes
network calls. Free, no API key. Kept strictly separate from `engine/`: the
target ranking works fully offline; weather only refines the GO/MARGINAL/
SKIP verdict on top of it, when reachable (see CLAUDE.md's Leitprinzip and
the M4 milestone note).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime

from nachtlotse.engine.models import WeatherSummary

_API_URL = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT_S = 10.0
_FORECAST_DAYS = 16  # Open-Meteo's max for the free hourly forecast — covers
# `lotse plan --date` for any night within that horizon, not just tonight.
_HOURLY_FIELDS = (
    "cloudcover,windspeed_10m,relative_humidity_2m,dew_point_2m,temperature_2m"
)


class WeatherUnavailable(Exception):
    """Weather couldn't be fetched or parsed — network, API, or format issue.

    Callers must treat this as routine, not exceptional: weather is an
    optional layer, and the target ranking must keep working without it.
    """


@dataclass(frozen=True)
class HourlyWeather:
    """Forecast for one UTC hour."""

    when: datetime
    cloud_cover_pct: float
    wind_speed_kmh: float
    humidity_pct: float
    dew_point_c: float
    temperature_c: float


def fetch_hourly(lat_deg: float, lon_deg: float) -> list[HourlyWeather]:
    """Hourly forecast for a location, from Open-Meteo.

    Raises `WeatherUnavailable` on any network, HTTP, or parsing failure.
    """
    params = {
        "latitude": f"{lat_deg:.5f}",
        "longitude": f"{lon_deg:.5f}",
        "hourly": _HOURLY_FIELDS,
        "timezone": "UTC",
        "forecast_days": str(_FORECAST_DAYS),
    }
    url = f"{_API_URL}?{urllib.parse.urlencode(params)}"

    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT_S) as response:
            raw = response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise WeatherUnavailable(f"Open-Meteo request failed: {exc}") from exc

    try:
        payload = json.loads(raw)
        hourly = payload["hourly"]
        rows = zip(
            hourly["time"],
            hourly["cloudcover"],
            hourly["windspeed_10m"],
            hourly["relative_humidity_2m"],
            hourly["dew_point_2m"],
            hourly["temperature_2m"],
            strict=True,
        )
        return [
            HourlyWeather(
                when=datetime.fromisoformat(t).replace(tzinfo=UTC),
                cloud_cover_pct=float(cloud),
                wind_speed_kmh=float(wind),
                humidity_pct=float(humidity),
                dew_point_c=float(dew_point),
                temperature_c=float(temperature),
            )
            for t, cloud, wind, humidity, dew_point, temperature in rows
        ]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise WeatherUnavailable(f"Open-Meteo response malformed: {exc}") from exc


def summarize_window(
    hours: list[HourlyWeather], start: datetime, end: datetime
) -> WeatherSummary | None:
    """Aggregate the hourly forecasts falling within [start, end].

    None if no forecast hour falls in the window (e.g. the window is
    further out than Open-Meteo's forecast horizon).
    """
    relevant = [hour for hour in hours if start <= hour.when <= end]
    if not relevant:
        return None

    return WeatherSummary(
        max_cloud_cover_pct=max(hour.cloud_cover_pct for hour in relevant),
        avg_cloud_cover_pct=sum(hour.cloud_cover_pct for hour in relevant)
        / len(relevant),
        max_wind_kmh=max(hour.wind_speed_kmh for hour in relevant),
        min_dew_point_spread_c=min(
            hour.temperature_c - hour.dew_point_c for hour in relevant
        ),
    )

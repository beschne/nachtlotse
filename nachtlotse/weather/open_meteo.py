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
from pathlib import Path

from nachtlotse.engine.models import WeatherSummary

_API_URL = "https://api.open-meteo.com/v1/forecast"
_TIMEOUT_S = 10.0

# Open-Meteo's own models refresh every 1-6h depending on model — polling
# faster than that buys nothing. Short enough that a plan run never works
# from meaningfully stale data; long enough that comparing several sites
# (see `best_sky.py`) doesn't cost one network round-trip per site every
# time you rerun it during the same evening's decision-making.
CACHE_TTL_HOURS = 1.0
DEFAULT_CACHE_DIR = Path(".cache/open_meteo")
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
        rows = list(
            zip(
                hourly["time"],
                hourly["cloudcover"],
                hourly["windspeed_10m"],
                hourly["relative_humidity_2m"],
                hourly["dew_point_2m"],
                hourly["temperature_2m"],
                strict=True,
            )
        )
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        raise WeatherUnavailable(f"Open-Meteo response malformed: {exc}") from exc

    # Open-Meteo leaves a handful of hours at the far edge of its forecast
    # horizon as `null` across every field (observed on the 16-day hourly
    # forecast) — that's a gap in a few hours, not a malformed response, so
    # those hours are dropped rather than discarding the whole fetch over
    # a `float(None)` failure.
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
        if None not in (cloud, wind, humidity, dew_point, temperature)
    ]


def _cache_path(cache_dir: Path, lat_deg: float, lon_deg: float) -> Path:
    # 3 decimals (~111 m) — more precision than any site's own coordinate
    # buys nothing at forecast-model resolution.
    return cache_dir / f"{lat_deg:.3f}_{lon_deg:.3f}.json"


def _read_cache(path: Path) -> list[HourlyWeather] | None:
    """A fresh, well-formed cache entry, or None on miss/expiry/corruption.

    Corruption isn't an error here — the cache is a pure optimization, so
    anything wrong with it just means falling back to a normal fetch.
    """
    try:
        payload = json.loads(path.read_text())
        fetched_at = datetime.fromisoformat(payload["fetched_at"])
        age_hours = (datetime.now(UTC) - fetched_at).total_seconds() / 3600.0
        if age_hours >= CACHE_TTL_HOURS:
            return None
        return [
            HourlyWeather(
                when=datetime.fromisoformat(row["when"]),
                cloud_cover_pct=row["cloud_cover_pct"],
                wind_speed_kmh=row["wind_speed_kmh"],
                humidity_pct=row["humidity_pct"],
                dew_point_c=row["dew_point_c"],
                temperature_c=row["temperature_c"],
            )
            for row in payload["hours"]
        ]
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        return None


def _write_cache(path: Path, hours: list[HourlyWeather]) -> None:
    payload = {
        "fetched_at": datetime.now(UTC).isoformat(),
        "hours": [
            {
                "when": hour.when.isoformat(),
                "cloud_cover_pct": hour.cloud_cover_pct,
                "wind_speed_kmh": hour.wind_speed_kmh,
                "humidity_pct": hour.humidity_pct,
                "dew_point_c": hour.dew_point_c,
                "temperature_c": hour.temperature_c,
            }
            for hour in hours
        ],
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
    except OSError:
        pass  # best-effort — a stale/missing cache just means a re-fetch


def fetch_hourly_cached(
    lat_deg: float, lon_deg: float, *, cache_dir: Path | None = None
) -> list[HourlyWeather]:
    """Same as `fetch_hourly`, but serves a same-site forecast already
    fetched within the last `CACHE_TTL_HOURS` from `cache_dir` (default:
    `DEFAULT_CACHE_DIR`, re-read here rather than bound as a default
    argument so tests can monkeypatch it) instead of calling Open-Meteo
    again. `WeatherUnavailable` still propagates from the underlying
    fetch exactly as `fetch_hourly` raises it.
    """
    if cache_dir is None:
        cache_dir = DEFAULT_CACHE_DIR
    path = _cache_path(cache_dir, lat_deg, lon_deg)
    cached = _read_cache(path)
    if cached is not None:
        return cached

    hours = fetch_hourly(lat_deg, lon_deg)
    _write_cache(path, hours)
    return hours


def hourly_forecast_in_window(
    hours: list[HourlyWeather], start: datetime, end: datetime
) -> list[HourlyWeather]:
    """Every forecast hour falling within [start, end], in order —
    the same window `summarize_window` collapses into one aggregate,
    kept hour-by-hour instead for ROADMAP.md's "Hourly cloud cover for
    the astro-night": a fully-clear window that closes early, or a
    socked-in one that clears at 2am, shows up as a shape rather than
    one averaged number.
    """
    return [hour for hour in hours if start <= hour.when <= end]


def summarize_window(
    hours: list[HourlyWeather], start: datetime, end: datetime
) -> WeatherSummary | None:
    """Aggregate the hourly forecasts falling within [start, end].

    None if no forecast hour falls in the window (e.g. the window is
    further out than Open-Meteo's forecast horizon).
    """
    relevant = hourly_forecast_in_window(hours, start, end)
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

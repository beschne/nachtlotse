"""Cross-site weather comparison tests (`best_sky.compare_sites`)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from nachtlotse import best_sky
from nachtlotse.engine import constraints
from nachtlotse.engine.models import HorizonProfile, Site
from nachtlotse.weather import open_meteo

BAD_HOMBURG = Site(
    name="Bad Homburg",
    lat_deg=50.2266,
    lon_deg=8.6180,
    elevation_m=190.0,
    tz="Europe/Berlin",
    horizon=HorizonProfile(points=[]),
)

# ~300 km from Bad Homburg — far enough to exercise a radius filter without
# landing exactly on some rounding edge.
MUNICH = Site(
    name="Munich",
    lat_deg=48.1372,
    lon_deg=11.5755,
    elevation_m=520.0,
    tz="Europe/Berlin",
    horizon=HorizonProfile(points=[]),
)

# ~15 km from Bad Homburg — well within a 50 km radius of it.
FRANKFURT = Site(
    name="Frankfurt",
    lat_deg=50.1109,
    lon_deg=8.6821,
    elevation_m=112.0,
    tz="Europe/Berlin",
    horizon=HorizonProfile(points=[]),
)

_NOW = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _isolated_weather_cache(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Every test below drives `best_sky.compare_sites`, which goes
    through `open_meteo.fetch_hourly_cached`'s real on-disk cache unless
    redirected — autoused so no test can write fake weather data into
    the project's actual `.cache/open_meteo/` cache. That's exactly what
    a one-off manual verification script did against real site
    coordinates (outside the test suite, but the same underlying
    mistake) and it broke the live GUI's Best Sky tab until the cache
    was cleared by hand — this fixture is what keeps the *test suite*
    itself from ever doing the same.
    """
    monkeypatch.setattr(open_meteo, "DEFAULT_CACHE_DIR", tmp_path)


def _fake_fetch_hourly_factory(cloud_cover_pct: float):
    def _fake_fetch_hourly(lat_deg: float, lon_deg: float) -> list:
        base = _NOW.replace(minute=0, second=0, microsecond=0)
        return [
            open_meteo.HourlyWeather(
                when=base + timedelta(hours=offset),
                cloud_cover_pct=cloud_cover_pct,
                wind_speed_kmh=5.0,
                humidity_pct=50.0,
                dew_point_c=5.0,
                temperature_c=15.0,
            )
            for offset in range(-24, 72)
        ]

    return _fake_fetch_hourly


def test_compare_sites_keeps_every_candidate_without_a_radius(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(open_meteo, "fetch_hourly", _fake_fetch_hourly_factory(10.0))

    reports = best_sky.compare_sites(
        BAD_HOMBURG, [BAD_HOMBURG, FRANKFURT, MUNICH], _NOW
    )

    assert {report.site.name for report in reports} == {
        "Bad Homburg",
        "Frankfurt",
        "Munich",
    }


def test_compare_sites_drops_candidates_outside_the_radius(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(open_meteo, "fetch_hourly", _fake_fetch_hourly_factory(10.0))

    reports = best_sky.compare_sites(
        BAD_HOMBURG, [BAD_HOMBURG, FRANKFURT, MUNICH], _NOW, max_distance_km=50.0
    )

    assert {report.site.name for report in reports} == {"Bad Homburg", "Frankfurt"}


def test_compare_sites_reports_a_plausible_distance() -> None:
    reports = best_sky.compare_sites(BAD_HOMBURG, [MUNICH], _NOW)

    (report,) = reports
    # Straight-line Bad Homburg-Munich distance is ~300 km; a generous
    # tolerance keeps this a sanity check, not a geodesy regression test.
    assert 280.0 <= report.distance_km <= 320.0


def test_compare_sites_ranks_clearest_night_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fetch_by_site(lat_deg: float, lon_deg: float) -> list:
        cloud_cover_pct = 80.0 if lat_deg == pytest.approx(FRANKFURT.lat_deg) else 5.0
        return _fake_fetch_hourly_factory(cloud_cover_pct)(lat_deg, lon_deg)

    monkeypatch.setattr(open_meteo, "fetch_hourly", fetch_by_site)

    reports = best_sky.compare_sites(BAD_HOMBURG, [FRANKFURT, MUNICH], _NOW)

    assert [report.site.name for report in reports] == ["Munich", "Frankfurt"]


def test_compare_sites_sorts_unreachable_weather_last(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def flaky_fetch(lat_deg: float, lon_deg: float) -> list:
        if lat_deg == pytest.approx(FRANKFURT.lat_deg):
            raise open_meteo.WeatherUnavailable("simulated: no network")
        return _fake_fetch_hourly_factory(50.0)(lat_deg, lon_deg)

    monkeypatch.setattr(open_meteo, "fetch_hourly", flaky_fetch)

    reports = best_sky.compare_sites(BAD_HOMBURG, [FRANKFURT, MUNICH], _NOW)

    assert [report.site.name for report in reports] == ["Munich", "Frankfurt"]
    assert reports[-1].weather is None
    assert reports[-1].hourly_cloud_cover == []
    assert reports[-1].weather_unavailable_reason == "unreachable"


def test_compare_sites_flags_a_night_beyond_the_forecast_horizon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful fetch that simply doesn't cover the requested night
    (e.g. a date picked weeks ahead, past Open-Meteo's own forecast
    horizon) must read as `weather_unavailable_reason ==
    "beyond_forecast_horizon"`, not the same generic "unreachable" a
    real fetch failure gets — see best_sky.WeatherUnavailableReason."""

    def fetch_far_from_now(lat_deg: float, lon_deg: float) -> list:
        # Real hours, real fetch — just nowhere near `_NOW`'s own dark
        # window, the same shape a too-far-out forecast horizon leaves.
        far_away = _NOW + timedelta(days=60)
        return [
            open_meteo.HourlyWeather(
                when=far_away.replace(minute=0, second=0, microsecond=0)
                + timedelta(hours=offset),
                cloud_cover_pct=10.0,
                wind_speed_kmh=5.0,
                humidity_pct=50.0,
                dew_point_c=5.0,
                temperature_c=15.0,
            )
            for offset in range(24)
        ]

    monkeypatch.setattr(open_meteo, "fetch_hourly", fetch_far_from_now)

    (report,) = best_sky.compare_sites(BAD_HOMBURG, [BAD_HOMBURG], _NOW)

    assert report.weather is None
    assert report.hourly_cloud_cover == []
    assert report.weather_unavailable_reason == "beyond_forecast_horizon"


def test_compare_sites_reuses_the_disk_cache_across_a_different_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`fetch_hourly_cached`'s on-disk cache is keyed by each candidate's
    own lat/lon (see `open_meteo._cache_path`) — never by which site is
    the current `reference`. So the GUI's Best Sky tab changing Center
    and clicking Refresh again must not re-fetch a candidate whose
    weather (summary *and* hourly, both drawn from that one cached
    fetch) is already on disk within the TTL, even though `reference`
    itself, and therefore every distance/bearing/ranking, is different
    the second time. (Cache isolation itself comes from the autouse
    `_isolated_weather_cache` fixture above.)"""
    call_count = 0

    def counting_fetch(lat_deg: float, lon_deg: float) -> list:
        nonlocal call_count
        call_count += 1
        return _fake_fetch_hourly_factory(10.0)(lat_deg, lon_deg)

    monkeypatch.setattr(open_meteo, "fetch_hourly", counting_fetch)

    candidates = [BAD_HOMBURG, FRANKFURT, MUNICH]
    best_sky.compare_sites(BAD_HOMBURG, candidates, _NOW)
    assert call_count == 3

    best_sky.compare_sites(FRANKFURT, candidates, _NOW)  # a different reference
    assert call_count == 3, (
        "changing the reference re-fetched already-cached candidates"
    )


def test_compare_sites_includes_hourly_cloud_cover_clipped_to_the_dark_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(open_meteo, "fetch_hourly", _fake_fetch_hourly_factory(10.0))

    (report,) = best_sky.compare_sites(BAD_HOMBURG, [BAD_HOMBURG], _NOW)

    assert report.hourly_cloud_cover, "the fake fetch spans well past the dark window"
    assert all(hour.cloud_cover_pct == 10.0 for hour in report.hourly_cloud_cover)
    # Every hour actually falls in that night's dark window, not just
    # somewhere in the fake fetch's wide -24h/+72h span.
    evening_start, morning_end = constraints.dark_window(BAD_HOMBURG, _NOW)
    assert all(
        evening_start <= hour.when <= morning_end for hour in report.hourly_cloud_cover
    )


def test_compass_direction_rounds_to_the_nearest_16_point() -> None:
    assert best_sky.compass_direction(0.0) == "N"
    assert best_sky.compass_direction(90.0) == "E"
    assert best_sky.compass_direction(200.0) == "SSW"
    assert best_sky.compass_direction(359.0) == "N"  # wraps past 360


def test_distance_km_is_symmetric_and_zero_for_the_same_site() -> None:
    assert best_sky.distance_km(BAD_HOMBURG, BAD_HOMBURG) == pytest.approx(
        0.0, abs=0.01
    )
    assert best_sky.distance_km(BAD_HOMBURG, MUNICH) == pytest.approx(
        best_sky.distance_km(MUNICH, BAD_HOMBURG)
    )

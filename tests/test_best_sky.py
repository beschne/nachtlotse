"""Cross-site weather comparison tests (`best_sky.compare_sites`)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from nachtlotse import best_sky
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

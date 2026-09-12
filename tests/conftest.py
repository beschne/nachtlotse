from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from nachtlotse.data import store
from nachtlotse.weather import open_meteo


@pytest.fixture(autouse=True)
def _no_real_weather_requests(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the whole suite offline: nothing should hit the real Open-Meteo
    API just because a test calls `lotse plan`. Defaults to a fixed
    clear-sky forecast spanning any plausible dark window; tests that care
    about specific weather (or its absence) can monkeypatch
    `open_meteo.fetch_hourly` again inside their own body to override this.

    Skipped for test_open_meteo.py itself, which tests the real
    `fetch_hourly` by mocking `urllib.request.urlopen` directly — already
    offline-safe on its own, and would otherwise never see its own mocks.
    """
    if request.module.__name__.rsplit(".", 1)[-1] == "test_open_meteo":
        return

    def _fake_fetch_hourly(
        lat_deg: float, lon_deg: float
    ) -> list[open_meteo.HourlyWeather]:
        base = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        return [
            open_meteo.HourlyWeather(
                when=base + timedelta(hours=offset),
                cloud_cover_pct=10.0,
                wind_speed_kmh=5.0,
                humidity_pct=50.0,
                dew_point_c=5.0,
                temperature_c=15.0,
            )
            for offset in range(-24, 72)
        ]

    monkeypatch.setattr(open_meteo, "fetch_hourly", _fake_fetch_hourly)


@pytest.fixture
def template_sites(monkeypatch: pytest.MonkeyPatch) -> list[store.SiteRecord]:
    """Monkeypatch store.SITES to the committed template's two examples.

    Decouples tests from whatever a developer's own gitignored
    sites_local.yaml happens to contain — or whether it exists at all — so
    the suite passes identically on a fresh clone.
    """
    records = store._parse_sites_yaml(store._TEMPLATE_SITES_PATH)
    monkeypatch.setattr(store, "SITES", records)
    return records


@pytest.fixture
def template_rigs(monkeypatch: pytest.MonkeyPatch) -> list[store.RigRecord]:
    """Monkeypatch store.RIGS to the committed template's four examples.

    Decouples tests from whatever a developer's own gitignored
    rigs_local.yaml happens to contain — or whether it exists at all — so
    the suite passes identically on a fresh clone.
    """
    records = store._parse_rigs_yaml(store._TEMPLATE_RIGS_PATH)
    monkeypatch.setattr(store, "RIGS", records)
    return records

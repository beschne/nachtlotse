from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from nachtlotse import cli, planning
from nachtlotse.data import store


def test_plan_command_prints_dark_window_moon_and_a_ranked_table(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["plan"])
    assert exit_code == 0

    output = capsys.readouterr().out
    assert template_sites[0].site.name in output
    assert template_rigs[0].rig.name in output
    assert "Dark window:" in output
    assert "Moon:" in output
    assert "Weather:" in output
    assert "Verdict:" in output

    default_site = store.default_site_record().site
    default_rig = store.default_rig_record().rig
    ranked = planning.rank_targets(default_site, default_rig, datetime.now(UTC))
    for target, *_rest in ranked:
        assert target.catalog_id in output


def test_plan_command_accepts_a_site_by_name_or_alias(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["plan", "--site", "Sternwarte"]) == 0
    output = capsys.readouterr().out
    assert "Volkssternwarte Hochtaunus" in output


def test_plan_command_accepts_a_rig_by_name_or_alias(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["plan", "--rig", "S50P"]) == 0
    output = capsys.readouterr().out
    assert "ZWO Seestar S50 Pro" in output


def test_plan_command_accepts_a_date_and_uses_that_nights_dark_window(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["plan", "--date", "2026-11-14"])
    assert exit_code == 0

    output = capsys.readouterr().out
    assert "Dark window: 2026-11-14" in output
    # Weather is far beyond Open-Meteo's forecast horizon, so this must
    # fall back gracefully rather than error.
    assert "Weather: unavailable" in output
    assert "Verdict:" in output


def test_plan_command_rejects_a_malformed_date(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["plan", "--date", "14.11.2026"])
    assert exit_code == 2
    assert "Invalid --date" in capsys.readouterr().err


def test_plan_command_rejects_an_unknown_site(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["plan", "--site", "Nirgendwo"])
    assert exit_code == 2


def test_plan_command_rejects_an_unknown_rig(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["plan", "--rig", "Nichtvorhanden"])
    assert exit_code == 2


def test_plan_command_reports_the_setup_hint_when_no_sites_are_configured(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(store, "SITES", [])
    exit_code = cli.main(["plan"])
    assert exit_code == 2
    assert "No observing sites configured" in capsys.readouterr().err


def test_plan_command_reports_the_setup_hint_when_no_rigs_are_configured(
    template_sites: list[store.SiteRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(store, "RIGS", [])
    exit_code = cli.main(["plan"])
    assert exit_code == 2
    assert "No rigs configured" in capsys.readouterr().err


def test_sites_command_lists_every_known_site(
    template_sites: list[store.SiteRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["sites"])
    assert exit_code == 0

    output = capsys.readouterr().out
    for record in template_sites:
        assert record.site.name in output


def test_sites_command_reports_the_setup_hint_when_nothing_is_configured(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(store, "SITES", [])
    exit_code = cli.main(["sites"])
    assert exit_code == 2
    assert "No observing sites configured" in capsys.readouterr().err


def test_rigs_command_lists_every_known_rig(
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["rigs"])
    assert exit_code == 0

    output = capsys.readouterr().out
    for record in template_rigs:
        assert record.rig.name in output


def test_rigs_command_reports_the_setup_hint_when_nothing_is_configured(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(store, "RIGS", [])
    exit_code = cli.main(["rigs"])
    assert exit_code == 2
    assert "No rigs configured" in capsys.readouterr().err


def test_plan_command_skips_on_overcast_weather(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """M4 DoD: overcast sky -> SKIP with the reason named in the output."""
    from nachtlotse.weather import open_meteo

    def overcast_everywhere(lat_deg: float, lon_deg: float) -> list:
        base = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        return [
            open_meteo.HourlyWeather(
                when=base + timedelta(hours=offset),
                cloud_cover_pct=95.0,
                wind_speed_kmh=5.0,
                humidity_pct=80.0,
                dew_point_c=5.0,
                temperature_c=15.0,
            )
            for offset in range(-24, 72)
        ]

    monkeypatch.setattr(open_meteo, "fetch_hourly", overcast_everywhere)

    assert cli.main(["plan"]) == 0
    output = capsys.readouterr().out

    assert "Verdict: SKIP" in output
    assert "cloud cover" in output.lower()


def test_plan_command_falls_back_gracefully_when_weather_is_unavailable(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Weather is an optional layer — no network must not break the ranking."""
    from nachtlotse.weather import open_meteo

    def always_unavailable(lat_deg: float, lon_deg: float) -> list:
        raise open_meteo.WeatherUnavailable("simulated: no network")

    monkeypatch.setattr(open_meteo, "fetch_hourly", always_unavailable)

    assert cli.main(["plan"]) == 0
    output = capsys.readouterr().out

    assert "Weather: unavailable" in output
    assert "Verdict:" in output  # still produced, from sky geometry alone
    assert "Best time (local)" in output  # the ranked table still printed


def test_unknown_command_is_rejected() -> None:
    with pytest.raises(SystemExit):
        cli.main(["nonsense"])

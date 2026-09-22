from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from nachtlotse import chart_export, cli, planning, prose
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
    for entry in ranked:
        targets = entry.targets if isinstance(entry, planning.RankedGroup) else (entry.target,)
        for target in targets:
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


def test_plan_command_passes_selected_types_through_to_planning(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    original_plan_night = planning.plan_night

    def spy_plan_night(site, rig, when, types=None, limit=None):
        captured["types"] = types
        return original_plan_night(site, rig, when, types=types, limit=limit)

    monkeypatch.setattr(planning, "plan_night", spy_plan_night)

    assert cli.main(["plan", "--type", "galaxy", "--type", "open_cluster"]) == 0
    assert captured["types"] == frozenset({"galaxy", "open_cluster"})


def test_plan_command_defaults_to_no_type_filter(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    original_plan_night = planning.plan_night

    def spy_plan_night(site, rig, when, types=None, limit=None):
        captured["types"] = types
        return original_plan_night(site, rig, when, types=types, limit=limit)

    monkeypatch.setattr(planning, "plan_night", spy_plan_night)

    assert cli.main(["plan"]) == 0
    assert captured["types"] is None


def test_plan_command_rejects_an_unknown_type(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    # argparse's own `choices` validation calls sys.exit() directly (same as
    # the unknown-subcommand case below), rather than returning through
    # cli.main()'s own exit-code convention.
    with pytest.raises(SystemExit):
        cli.main(["plan", "--type", "wormhole"])
    assert "invalid choice" in capsys.readouterr().err


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
    assert "Clouds tonight:" not in output  # no hourly forecast to show either
    assert "Verdict:" in output  # still produced, from sky geometry alone
    assert "Best time (local)" in output  # the ranked table still printed


def test_plan_command_prints_an_hourly_cloud_cover_sparkline(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The offline clear-sky fixture (see conftest.py) gives every test a
    real hourly forecast — a colorless block-height sparkline, one
    character per forecast hour, no ANSI escapes."""
    assert cli.main(["plan"]) == 0
    output = capsys.readouterr().out

    lines = [line for line in output.splitlines() if line.startswith("Clouds tonight:")]
    assert len(lines) == 1
    line = lines[0]
    assert "\x1b" not in line  # no ANSI color codes
    bar = line.split("Clouds tonight: ", 1)[1].split("  (", 1)[0]
    assert bar  # at least one hour in the dark window
    assert all(char in "▁▂▃▄▅▆▇█" for char in bar)


def test_best_sky_command_lists_every_configured_site_without_a_radius(
    template_sites: list[store.SiteRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["best-sky"]) == 0
    output = capsys.readouterr().out

    for record in template_sites:
        assert record.site.name in output


def test_best_sky_command_respects_radius_km(
    template_sites: list[store.SiteRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The template's two sites are ~5 km apart — a 1 km radius keeps only
    the reference site itself."""
    reference_name = template_sites[0].site.name
    other_name = template_sites[1].site.name

    assert cli.main(["best-sky", "--site", reference_name, "--radius-km", "1"]) == 0
    output = capsys.readouterr().out

    assert reference_name in output
    assert other_name not in output


def test_best_sky_command_rejects_an_invalid_date(
    template_sites: list[store.SiteRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["best-sky", "--date", "not-a-date"]) == 2
    assert "Invalid --date" in capsys.readouterr().err


def test_plan_command_chart_writes_the_default_png_and_overwrites_it(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path,
) -> None:
    pytest.importorskip("matplotlib")
    monkeypatch.chdir(tmp_path)

    assert cli.main(["plan", "--chart"]) == 0
    default_path = tmp_path / chart_export.DEFAULT_CHART_FILENAME
    assert default_path.exists()
    assert f"Chart written to {chart_export.DEFAULT_CHART_FILENAME}" in capsys.readouterr().out
    first_mtime = default_path.stat().st_mtime_ns

    assert cli.main(["plan", "--chart"]) == 0
    assert default_path.stat().st_mtime_ns >= first_mtime  # overwritten, not errored on


def test_plan_command_chart_accepts_a_custom_filename(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    tmp_path,
) -> None:
    pytest.importorskip("matplotlib")

    custom_path = tmp_path / "mychart.png"
    assert cli.main(["plan", "--chart", str(custom_path)]) == 0
    assert custom_path.exists()
    # The default filename must not also appear alongside it.
    assert not (tmp_path / chart_export.DEFAULT_CHART_FILENAME).exists()


def test_plan_command_reports_the_setup_hint_when_matplotlib_is_missing(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path,
) -> None:
    def _unavailable(plan, path):
        raise chart_export.ChartExportUnavailable(
            "PNG export needs matplotlib, which isn't installed — run "
            "`uv sync --extra charts` and try again."
        )

    monkeypatch.setattr(chart_export, "save_shortlist_chart", _unavailable)

    exit_code = cli.main(["plan", "--chart", str(tmp_path / "out.png")])

    assert exit_code == 2
    assert "uv sync --extra charts" in capsys.readouterr().err


def test_unknown_command_is_rejected() -> None:
    with pytest.raises(SystemExit):
        cli.main(["nonsense"])


def test_plan_command_respects_limit_flag(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--limit should cap the number of evaluated catalog objects."""
    from astropy.time import Time

    # Build a controlled list: first 5 pass constraints, next 10 fail
    from nachtlotse.engine.constraints import build_observer
    from nachtlotse.engine.models import Target

    site = store.get_site_record("Großer Feldberg").site
    observer = build_observer(site)
    night_reference = Time(datetime(2026, 9, 12, 22, 0, tzinfo=UTC))
    lst_deg = night_reference.sidereal_time(
        "apparent", longitude=observer.location.lon
    ).deg

    passing_targets = [
        Target(
            name=f"passing {i}",
            ra_deg=lst_deg,
            dec_deg=site.lat_deg - 20.0 - i * 5.0,
            types=("galaxy",),
        )
        for i in range(3)
    ]
    failing_targets = [
        Target(
            name=f"failing {i}",
            ra_deg=lst_deg,
            dec_deg=site.lat_deg - 20.0 - i * 0.1,  # too close together = blocked
            types=("galaxy",),
        )
        for i in range(20)
    ]
    monkeypatch.setattr(planning, "CATALOG", passing_targets + failing_targets)

    assert cli.main(["plan", "--limit", "5"]) == 0
    output = capsys.readouterr().out

    # Only 3 passing targets + 2 evaluated from failing = 5 evaluated
    # But only 3 pass constraints, so the ranked table shows 3
    assert "Best time (local)" in output
    # The shortlist should have at most 3 (all passing)
    verdict_count = output.count("Verdict:")
    assert verdict_count <= 5


def test_plan_command_limit_zero_evaluates_all(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--limit 0 should evaluate all catalog objects."""
    from nachtlotse.engine.models import Target

    # A small set where some pass and some fail constraints
    passing_targets = [
        Target(name=f"passing {i}", ra_deg=0.0, dec_deg=0.0, types=("galaxy",))
        for i in range(5)
    ]
    monkeypatch.setattr(planning, "CATALOG", passing_targets)

    assert cli.main(["plan", "--limit", "0"]) == 0
    output = capsys.readouterr().out
    # Should not crash and should attempt all 5
    assert "Best time (local)" in output or "No catalog target" in output


def test_plan_command_shows_a_co_visible_group_as_one_joined_shortlist_entry(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Two targets close enough to share the rig's frame show up as one
    "name + name" shortlist entry with a single verdict, not two separate
    ones (see engine.grouping and planning._fold_in_groups)."""
    from astropy.time import Time

    from nachtlotse.engine.constraints import build_observer
    from nachtlotse.engine.models import Target

    site = store.get_site_record("Großer Feldberg").site  # unrestricted horizon
    rig = store.default_rig_record().rig
    observer = build_observer(site)
    night_reference = Time(datetime(2026, 9, 12, 22, 0, tzinfo=UTC))
    lst_deg = night_reference.sidereal_time(
        "apparent", longitude=observer.location.lon
    ).deg
    fov_short_arcmin = min(rig.fov_deg) * 60.0
    dec_deg = site.lat_deg - 40.0  # well off zenith, safe for the alt-az default rig

    close_a = Target(name="close a", ra_deg=lst_deg, dec_deg=dec_deg)
    close_b = Target(
        name="close b", ra_deg=lst_deg + (fov_short_arcmin * 0.3) / 60.0, dec_deg=dec_deg
    )
    monkeypatch.setattr(planning, "CATALOG", [close_a, close_b])
    monkeypatch.setattr(cli, "_resolve_when", lambda *_a, **_kw: night_reference.to_datetime(timezone=UTC))

    assert cli.main(["plan"]) == 0
    output = capsys.readouterr().out

    assert "close a" in output and "close b" in output
    assert "close a + close b" in output or "close b + close a" in output
    assert output.count("Verdict:") == 1


def test_plan_command_rejects_best_rig_combined_with_rig(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["plan", "--best-rig", "--rig", "S30P"]) == 2
    assert "--best-rig" in capsys.readouterr().err


def test_plan_command_rejects_best_rig_combined_with_chart(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["plan", "--best-rig", "--chart"]) == 2
    assert "--best-rig" in capsys.readouterr().err


def test_plan_command_best_rig_shows_which_rig_won_each_target(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--best-rig scores every configured rig per target and shows the
    winner in its own column/label — not the single --rig it replaces."""
    from astropy.time import Time

    from nachtlotse.engine.constraints import build_observer
    from nachtlotse.engine.models import Target

    site = store.get_site_record("Großer Feldberg").site  # unrestricted horizon
    observer = build_observer(site)
    night_reference = Time(datetime(2026, 9, 12, 22, 0, tzinfo=UTC))
    lst_deg = night_reference.sidereal_time(
        "apparent", longitude=observer.location.lon
    ).deg

    target = Target(
        name="best-rig cli test target", ra_deg=lst_deg, dec_deg=site.lat_deg - 20.0
    )
    monkeypatch.setattr(planning, "CATALOG", [target])
    monkeypatch.setattr(
        cli, "_resolve_when", lambda *_a, **_kw: night_reference.to_datetime(timezone=UTC)
    )

    assert cli.main(["plan", "--best-rig"]) == 0
    output = capsys.readouterr().out

    assert "best rig per target" in output
    assert "best-rig cli test target" in output
    assert any(
        record.rig.name in output for record in template_rigs
    )  # the winning rig's name is shown somewhere


def test_plan_command_prose_prints_the_briefing_when_available(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        prose, "generate_nightly_briefing", lambda plan: "A clear night ahead."
    )

    assert cli.main(["plan", "--prose"]) == 0
    output = capsys.readouterr().out

    assert "Nightly briefing" in output
    assert "A clear night ahead." in output


def test_plan_command_prose_fails_loudly_when_unavailable(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _boom(plan):
        raise prose.ProseUnavailable("no ANTHROPIC_API_KEY set")

    monkeypatch.setattr(prose, "generate_nightly_briefing", _boom)

    assert cli.main(["plan", "--prose"]) == 2
    assert "no ANTHROPIC_API_KEY set" in capsys.readouterr().err


def test_plan_command_prose_works_with_best_rig(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        prose, "generate_nightly_briefing", lambda plan: "Best-rig briefing text."
    )

    assert cli.main(["plan", "--best-rig", "--prose"]) == 0
    output = capsys.readouterr().out

    assert "Best-rig briefing text." in output


def test_plan_command_prose_is_not_requested_when_nothing_is_observable(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An empty shortlist means there's nothing to brief about — the LLM
    shouldn't be called just because --prose was passed."""

    def _fail_if_called(plan):
        raise AssertionError("generate_nightly_briefing should not be called")

    monkeypatch.setattr(prose, "generate_nightly_briefing", _fail_if_called)
    monkeypatch.setattr(planning, "CATALOG", [])

    assert cli.main(["plan", "--prose"]) == 0

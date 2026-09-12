from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from nachtlotse import cli
from nachtlotse.data import store


def test_today_command_prints_dark_window_moon_and_a_ranked_table(
    template_sites: list[store.SiteRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["today"])
    assert exit_code == 0

    output = capsys.readouterr().out
    assert template_sites[0].site.name in output
    assert cli.SEESTAR_S30_PRO.name in output
    assert "Dark window:" in output
    assert "Moon:" in output

    default_site = store.default_site_record().site
    ranked = cli._rank_targets(default_site, datetime.now(UTC))
    for target, *_rest in ranked:
        assert target.catalog_id in output


def test_today_command_accepts_a_site_by_name_or_alias(
    template_sites: list[store.SiteRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["today", "--site", "Sternwarte"]) == 0
    output = capsys.readouterr().out
    assert "Volkssternwarte Hochtaunus" in output


def test_today_command_rejects_an_unknown_site(
    template_sites: list[store.SiteRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["today", "--site", "Nirgendwo"])
    assert exit_code == 2


def test_today_command_reports_the_setup_hint_when_nothing_is_configured(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(store, "SITES", [])
    exit_code = cli.main(["today"])
    assert exit_code == 2
    assert "No observing sites configured" in capsys.readouterr().err


def test_rank_targets_is_sorted_by_descending_altitude_and_passes_constraints(
    template_sites: list[store.SiteRecord],
) -> None:
    site = store.default_site_record().site
    ranked = cli._rank_targets(site, datetime.now(UTC))
    altitudes = [pos.alt_deg for _target, _best_time, pos in ranked]

    assert altitudes == sorted(altitudes, reverse=True)
    assert all(alt_deg > 0.0 for alt_deg in altitudes)


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


def test_a_heavily_obstructed_horizon_excludes_targets_a_clear_horizon_admits(
    template_sites: list[store.SiteRecord],
) -> None:
    """M2 DoD: the same sky yields different target lists at two sites with
    different horizons. Both sites share the built-in Feldberg's location —
    only the horizon profile differs.
    """
    from nachtlotse.engine.models import HorizonProfile

    now = datetime.now(UTC)
    base_site = store.get_site_record("Großer Feldberg").site
    open_site = base_site
    walled_site = replace(
        base_site, horizon=HorizonProfile(points=store._sector_to_points(348.0, 105.0))
    )

    open_ranked = {
        target.catalog_id for target, *_ in cli._rank_targets(open_site, now)
    }
    walled_ranked = {
        target.catalog_id for target, *_ in cli._rank_targets(walled_site, now)
    }

    assert open_ranked != walled_ranked


def test_unknown_command_is_rejected() -> None:
    with pytest.raises(SystemExit):
        cli.main(["nonsense"])

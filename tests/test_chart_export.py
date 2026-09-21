"""Tests for the CLI's `--chart` PNG export (nachtlotse/chart_export.py).

matplotlib is an optional extra (`uv sync --extra charts`) — the
"missing dependency" path is tested by forcing the import seam to
fail, so it runs regardless of whether matplotlib happens to be
installed locally; the "renders a real PNG" tests need the real
library and skip (via `pytest.importorskip`) otherwise.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nachtlotse import chart_export, planning
from nachtlotse.data import store


def _plan_with_shortlist(site, rig) -> planning.NightPlan:
    now = datetime.now(UTC)
    return planning.plan_night(site, rig, now)


def _empty_plan(site, rig) -> planning.NightPlan:
    now = datetime.now(UTC)
    return planning.NightPlan(
        site=site,
        rig=rig,
        evening_start=now,
        morning_end=now,
        moon_illumination_pct=0.0,
        moonrise=None,
        moonset=None,
        weather=None,
        hourly_cloud_cover=[],
        ranked=[],
        shortlist=[],
    )


def test_save_shortlist_chart_raises_when_matplotlib_is_unavailable(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    site = store.default_site_record().site
    rig = store.default_rig_record().rig
    plan = _plan_with_shortlist(site, rig)

    def _boom():
        raise ImportError("simulated: matplotlib not installed")

    monkeypatch.setattr(chart_export, "_import_matplotlib", _boom)

    with pytest.raises(chart_export.ChartExportUnavailable, match="charts"):
        chart_export.save_shortlist_chart(plan, tmp_path / "out.png")


def test_save_shortlist_chart_raises_on_an_empty_shortlist(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    tmp_path,
) -> None:
    site = store.default_site_record().site
    rig = store.default_rig_record().rig

    with pytest.raises(ValueError, match="empty"):
        chart_export.save_shortlist_chart(_empty_plan(site, rig), tmp_path / "out.png")


def test_save_shortlist_chart_writes_and_overwrites_a_png(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    tmp_path,
) -> None:
    pytest.importorskip("matplotlib")

    site = store.default_site_record().site
    rig = store.default_rig_record().rig
    plan = _plan_with_shortlist(site, rig)
    path = tmp_path / "chart.png"

    chart_export.save_shortlist_chart(plan, path)
    assert path.exists()
    first_size = path.stat().st_size
    assert first_size > 0

    # Overwrite: same path, must succeed again rather than erroring on an
    # existing file.
    chart_export.save_shortlist_chart(plan, path)
    assert path.exists()

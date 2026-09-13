"""Smoke tests for the Streamlit MVP (M5) via streamlit's AppTest harness.

Runs the real script in a simulated session — no browser needed — so a
broken import or a bad `st.*` call fails the suite the same way a broken
`lotse plan` would.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# streamlit is an optional extra (`uv sync --extra ui`), not a core
# dependency — skip this whole module rather than fail collection when
# it isn't installed (e.g. a bare clone running the core test suite).
pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest

from nachtlotse.data import store
from nachtlotse.data.catalog import CATALOG
from nachtlotse.engine.models import TARGET_TYPE_LABELS

_APP_PATH = str(Path(__file__).resolve().parents[1] / "nachtlotse" / "ui" / "app.py")


def test_app_runs_without_exceptions_and_shows_a_verdict(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
) -> None:
    at = AppTest.from_file(_APP_PATH, default_timeout=60).run()

    assert not at.exception
    assert len(at.selectbox) == 2
    site_select, rig_select = at.selectbox
    assert site_select.value == template_sites[0].site.name
    assert rig_select.value == template_rigs[0].rig.name

    # Either a GO/MARGINAL/SKIP verdict box, or the explicit "nothing
    # observable tonight" fallback — both are valid outcomes depending on
    # today's real sky, but the app must always land on one of them.
    verdict_boxes = list(at.success) + list(at.warning) + list(at.error)
    assert verdict_boxes, "expected a verdict or a fallback message"


def test_app_shows_setup_hint_when_no_sites_are_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "SITES", [])
    at = AppTest.from_file(_APP_PATH, default_timeout=60).run()

    assert not at.exception
    assert any("No observing sites configured" in e.value for e in at.error)


def test_app_shows_setup_hint_when_no_rigs_are_configured(
    template_sites: list[store.SiteRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "RIGS", [])
    at = AppTest.from_file(_APP_PATH, default_timeout=60).run()

    assert not at.exception
    assert any("No rigs configured" in e.value for e in at.error)


def test_selecting_an_object_type_filters_the_plan_to_that_type(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
) -> None:
    assert any("galaxy" in t.types for t in CATALOG)  # sanity: fixture has galaxies

    at = AppTest.from_file(_APP_PATH, default_timeout=60).run()
    assert len(at.multiselect) == 1
    # `.options` holds the format_func-rendered labels, not the raw
    # TargetType values `.select()` takes — hence the label lookup here.
    assert TARGET_TYPE_LABELS["galaxy"] in at.multiselect[0].options

    at = at.multiselect[0].select("galaxy").run()
    assert not at.exception

    # Whether anything is observable tonight is real-sky-dependent (same
    # caveat as the unfiltered smoke test above) — either outcome is valid,
    # but whichever happens must be internally consistent with the filter.
    if at.error and any("selected type" in e.value for e in at.error):
        return
    assert "Galaxy" in at.caption[-1].value  # hero's caption, not the page tagline
    if at.dataframe:
        assert all("Galaxy" in cell for cell in at.dataframe[0].value["Type"])


def test_switching_site_replans_without_exceptions(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
) -> None:
    at = AppTest.from_file(_APP_PATH, default_timeout=60).run()
    site_select = at.selectbox[0]

    other_site_name = next(
        record.site.name
        for record in template_sites
        if record.site.name != site_select.value
    )
    at = site_select.select(other_site_name).run()

    assert not at.exception
    assert f"{other_site_name} —" in at.subheader[0].value

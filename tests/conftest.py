from __future__ import annotations

import pytest

from nachtlotse.data import store


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

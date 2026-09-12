from __future__ import annotations

from pathlib import Path

import pytest

from nachtlotse.data import store


def test_template_file_parses_into_two_distinct_named_sites(
    template_sites: list[store.SiteRecord],
) -> None:
    names = {record.site.name for record in template_sites}
    assert names == {"Volkssternwarte Hochtaunus", "Großer Feldberg"}


def test_get_site_record_matches_by_exact_name(
    template_sites: list[store.SiteRecord],
) -> None:
    record = store.get_site_record("Großer Feldberg")
    assert record.site.name == "Großer Feldberg"


def test_get_site_record_matches_by_alias_case_insensitively(
    template_sites: list[store.SiteRecord],
) -> None:
    assert store.get_site_record("sternwarte").site.name == "Volkssternwarte Hochtaunus"
    assert store.get_site_record("feldberg").site.name == "Großer Feldberg"


def test_get_site_record_falls_back_to_a_unique_substring_match(
    template_sites: list[store.SiteRecord],
) -> None:
    record = store.get_site_record("Feldberg")
    assert record.site.name == "Großer Feldberg"


def test_get_site_record_raises_with_known_sites_listed_for_a_typo(
    template_sites: list[store.SiteRecord],
) -> None:
    with pytest.raises(ValueError, match="Unknown site"):
        store.get_site_record("Nirgendwo")


def test_get_site_record_raises_on_an_ambiguous_substring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nachtlotse.engine.models import HorizonProfile, Site

    fake_a = store.SiteRecord(
        site=Site(
            name="Test Site North",
            lat_deg=50.0,
            lon_deg=8.0,
            elevation_m=100.0,
            tz="Europe/Berlin",
            horizon=HorizonProfile(points=[]),
        ),
        region="",
        bortle="",
    )
    fake_b = store.SiteRecord(
        site=Site(
            name="Test Site South",
            lat_deg=50.0,
            lon_deg=8.0,
            elevation_m=100.0,
            tz="Europe/Berlin",
            horizon=HorizonProfile(points=[]),
        ),
        region="",
        bortle="",
    )
    monkeypatch.setattr(store, "SITES", [fake_a, fake_b])

    with pytest.raises(ValueError, match="Ambiguous site"):
        store.get_site_record("Test Site")


def test_default_site_record_is_the_first_configured_site(
    template_sites: list[store.SiteRecord],
) -> None:
    assert store.default_site_record().site.name == template_sites[0].site.name
    assert store.default_site_record().site.name == "Volkssternwarte Hochtaunus"


def test_require_sites_raises_a_helpful_error_pointing_at_the_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "SITES", [])
    with pytest.raises(ValueError, match="sites_local.template.yaml"):
        store.require_sites()


def test_get_site_record_raises_the_setup_hint_when_nothing_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "SITES", [])
    with pytest.raises(ValueError, match="No observing sites configured"):
        store.get_site_record("anything")


def test_default_site_record_raises_the_setup_hint_when_nothing_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "SITES", [])
    with pytest.raises(ValueError, match="No observing sites configured"):
        store.default_site_record()


def test_sector_to_points_marks_the_open_arc_clear_and_rest_walled() -> None:
    # "125-30": open clockwise from 125° through 0° to 30°; walled elsewhere.
    from nachtlotse.engine.models import HorizonProfile

    horizon = HorizonProfile(points=store._sector_to_points(125.0, 30.0))

    assert horizon.min_alt(180.0) == pytest.approx(0.0)  # inside the open arc
    assert horizon.min_alt(0.0) == pytest.approx(0.0)  # inside, across the wrap
    assert horizon.min_alt(75.0) == pytest.approx(90.0)  # inside the walled gap


def test_sector_to_points_full_circle_at_zero_altitude_is_unrestricted() -> None:
    assert store._sector_to_points(0.0, 360.0) == []


def test_load_local_sites_returns_empty_list_when_file_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store, "_LOCAL_SITES_PATH", tmp_path / "does-not-exist.yaml")
    assert store._load_local_sites() == []


def test_load_local_sites_parses_horizon_points_and_sector_shorthand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = tmp_path / "sites_local.yaml"
    yaml_path.write_text(
        """
- name: "Measured Site"
  lat_deg: 50.1
  lon_deg: 8.1
  elevation_m: 200.0
  region: "Test"
  bortle: "3"
  address: "Somewhere 1"
  aliases: ["MS"]
  horizon_points:
    - [0.0, 10.0]
    - [180.0, 5.0]
- name: "Sector Site"
  lat_deg: 50.2
  lon_deg: 8.2
  elevation_m: 300.0
  region: "Test"
  bortle: "2"
  sector: [100.0, 200.0, 15.0]
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(store, "_LOCAL_SITES_PATH", yaml_path)

    records = store._load_local_sites()
    by_name = {record.site.name: record for record in records}

    assert by_name["Measured Site"].site.horizon.points == [(0.0, 10.0), (180.0, 5.0)]
    assert by_name["Measured Site"].aliases == ("MS",)

    sector_horizon = by_name["Sector Site"].site.horizon
    assert sector_horizon.min_alt(150.0) == pytest.approx(15.0)  # inside the sector
    assert sector_horizon.min_alt(0.0) == pytest.approx(90.0)  # outside it

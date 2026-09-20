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


@pytest.mark.parametrize(
    "bortle_text,expected_class",
    [
        ("4", 4.0),
        ("5 (heavily light-polluted, urban fringe)", 5.0),
        ("3-4", 3.5),  # hyphen
        ("3–4", 3.5),  # en dash
        ("4–5 (light-polluted; forest cover helps to the south)", 4.5),
        ("", None),
    ],
)
def test_parse_bortle_class_extracts_a_numeric_class_from_free_text(
    bortle_text: str, expected_class: float | None
) -> None:
    result = store._parse_bortle_class(bortle_text)
    if expected_class is None:
        assert result is None
    else:
        assert result == pytest.approx(expected_class)


def test_load_local_sites_parses_bortle_class_and_measured_sky_brightness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = tmp_path / "sites_local.yaml"
    yaml_path.write_text(
        """
- name: "Measured Site"
  lat_deg: 50.1
  lon_deg: 8.1
  elevation_m: 200.0
  bortle: "4-5 (light-polluted; forest cover helps to the south)"
  zenith_sky_brightness_mag_arcsec2: 18.23
- name: "Estimate-Only Site"
  lat_deg: 50.2
  lon_deg: 8.2
  elevation_m: 300.0
  bortle: "2"
- name: "No-Bortle Site"
  lat_deg: 50.3
  lon_deg: 8.3
  elevation_m: 400.0
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(store, "_LOCAL_SITES_PATH", yaml_path)

    by_name = {
        record.site.name: record.site for record in store._load_local_sites()
    }

    measured = by_name["Measured Site"]
    assert measured.bortle_class == pytest.approx(4.5)
    assert measured.zenith_sky_brightness_mag_arcsec2 == pytest.approx(18.23)

    estimate_only = by_name["Estimate-Only Site"]
    assert estimate_only.bortle_class == pytest.approx(2.0)
    assert estimate_only.zenith_sky_brightness_mag_arcsec2 is None

    no_bortle = by_name["No-Bortle Site"]
    assert no_bortle.bortle_class is None
    assert no_bortle.zenith_sky_brightness_mag_arcsec2 is None


def test_template_file_parses_into_five_distinct_named_rigs(
    template_rigs: list[store.RigRecord],
) -> None:
    names = {record.rig.name for record in template_rigs}
    assert names == {
        "ZWO Seestar S30 Pro",
        "ZWO Seestar S30 Pro (EQ wedge)",
        "ZWO Seestar S50 Pro",
        "Redcat 51 with ASI2600MC Duo",
        "TEC AP 160/1120 f/7 FL",
    }


def test_s30_pro_altaz_and_eq_wedge_variants_share_optics_but_differ_in_mount(
    template_rigs: list[store.RigRecord],
) -> None:
    altaz = store.get_rig_record("S30P").rig
    eq_wedge = store.get_rig_record("S30P-EQ").rig

    assert altaz.mount.kind == "altaz"
    assert eq_wedge.mount.kind == "eq"
    assert altaz.optics.focal_length_mm == pytest.approx(
        eq_wedge.optics.focal_length_mm
    )
    assert altaz.sensor.pixel_um == pytest.approx(eq_wedge.sensor.pixel_um)


def test_get_rig_record_matches_by_alias_case_insensitively(
    template_rigs: list[store.RigRecord],
) -> None:
    assert store.get_rig_record("s30p").rig.name == "ZWO Seestar S30 Pro"
    assert store.get_rig_record("s50p").rig.name == "ZWO Seestar S50 Pro"


def test_get_rig_record_falls_back_to_a_unique_substring_match(
    template_rigs: list[store.RigRecord],
) -> None:
    record = store.get_rig_record("Redcat")
    assert record.rig.name == "Redcat 51 with ASI2600MC Duo"


def test_get_rig_record_raises_with_known_rigs_listed_for_a_typo(
    template_rigs: list[store.RigRecord],
) -> None:
    with pytest.raises(ValueError, match="Unknown rig"):
        store.get_rig_record("Nichtvorhanden")


def test_default_rig_record_is_the_first_configured_rig(
    template_rigs: list[store.RigRecord],
) -> None:
    assert store.default_rig_record().rig.name == template_rigs[0].rig.name
    assert store.default_rig_record().rig.name == "ZWO Seestar S30 Pro"


def test_require_rigs_raises_a_helpful_error_pointing_at_the_template(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(store, "RIGS", [])
    with pytest.raises(ValueError, match="rigs_local.template.yaml"):
        store.require_rigs()


def test_redcat_51_rig_has_an_eq_mount_and_correct_plate_scale(
    template_rigs: list[store.RigRecord],
) -> None:
    rig = store.get_rig_record("Redcat 51 with ASI2600MC Duo").rig
    assert rig.mount.kind == "eq"
    assert rig.optics.focal_length_mm == pytest.approx(250.0)
    assert rig.optics.aperture_mm == pytest.approx(51.0)
    assert rig.sensor.width_px == 6248
    assert rig.sensor.height_px == 4176
    # plate scale = 206.265 * pixel_um / focal_length_mm
    assert rig.sampling_arcsec_px == pytest.approx(206.265 * 3.76 / 250.0)


def test_load_local_rigs_returns_empty_list_when_file_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store, "_LOCAL_RIGS_PATH", tmp_path / "does-not-exist.yaml")
    assert store._load_local_rigs() == []


def test_load_local_rigs_parses_optics_sensor_and_mount(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = tmp_path / "rigs_local.yaml"
    yaml_path.write_text(
        """
- name: "Test Rig"
  aliases: ["TR"]
  optics:
    focal_length_mm: 100.0
    aperture_mm: 20.0
  sensor:
    name: "Test Sensor"
    width_px: 1000
    height_px: 500
    pixel_um: 4.0
  mount:
    kind: "eq"
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(store, "_LOCAL_RIGS_PATH", yaml_path)

    records = store._load_local_rigs()
    assert len(records) == 1
    record = records[0]

    assert record.rig.name == "Test Rig"
    assert record.aliases == ("TR",)
    assert record.rig.optics.focal_length_mm == pytest.approx(100.0)
    assert record.rig.sensor.width_px == 1000
    assert record.rig.mount.kind == "eq"
    assert record.rig.mount.zenith_avoid_deg is None


def test_load_prose_config_returns_none_when_file_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store, "_LOCAL_PROSE_PATH", tmp_path / "does-not-exist.yaml")
    assert store._load_local_prose() is None


def test_load_prose_config_parses_api_key_and_model(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = tmp_path / "prose_local.yaml"
    yaml_path.write_text(
        """
api_key: "sk-ant-test-key"
model: "claude-haiku-4-5-20251001"
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(store, "_LOCAL_PROSE_PATH", yaml_path)

    config = store._load_local_prose()

    assert config == store.ProseConfig(
        api_key="sk-ant-test-key", model="claude-haiku-4-5-20251001"
    )


def test_load_prose_config_allows_either_field_to_be_omitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    yaml_path = tmp_path / "prose_local.yaml"
    yaml_path.write_text('model: "claude-haiku-4-5-20251001"\n', encoding="utf-8")
    monkeypatch.setattr(store, "_LOCAL_PROSE_PATH", yaml_path)

    config = store._load_local_prose()

    assert config == store.ProseConfig(
        api_key=None, model="claude-haiku-4-5-20251001"
    )

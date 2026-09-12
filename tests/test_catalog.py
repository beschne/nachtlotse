from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from nachtlotse.data import catalog
from nachtlotse.data.catalog import CATALOG

# Expected (inclusive lower, exclusive upper) magnitude bound per bin file —
# `None` lower bound means "no floor" (the brightest bin). Update this
# alongside any new mag_*.yaml file; a coverage test below keeps it honest.
_BIN_BOUNDS: dict[str, tuple[float | None, float]] = {
    "mag_lt_6.yaml": (None, 6.0),
    "mag_6_7.yaml": (6.0, 7.0),
    "mag_7_8.yaml": (7.0, 8.0),
    "mag_8_9.yaml": (8.0, 9.0),
    "mag_9_10.yaml": (9.0, 10.0),
    "mag_10_11.yaml": (10.0, 11.0),
    "mag_11_12.yaml": (11.0, 12.0),
    "mag_12_13.yaml": (12.0, 13.0),
}

# Visibility/brightness policy for what belongs in this catalog at all:
# - Reach at least 20 deg altitude (this project's usual observability
#   floor, see engine.constraints) for an observer as far south as 40N —
#   the least favorable latitude among "northern hemisphere, 40N or
#   further north". At 40N, max altitude = 90 - 40 + dec, so this requires
#   dec >= -30 (M83 at -29.87 is the existing, deliberately-kept-in edge
#   case that pins this boundary).
# - No fainter than this project's own computed photographic ceiling: the
#   widest-aperture rig (Redcat 51, 51mm) under the darkest sky in scope
#   (Bortle 2) — see engine.framing.photographic_limiting_magnitude(51.0, 2.0).
_MIN_DEC_DEG_FOR_40N_VISIBILITY = -30.0
_MAX_CATALOG_MAGNITUDE = 18.6


def test_catalog_has_around_ninety_unique_objects() -> None:
    assert 80 <= len(CATALOG) <= 95


def test_catalog_ids_are_unique() -> None:
    catalog_ids = [target.catalog_id for target in CATALOG]
    assert len(catalog_ids) == len(set(catalog_ids))
    assert all(catalog_id.startswith(("M", "NGC", "IC")) for catalog_id in catalog_ids)


def test_catalog_targets_are_visible_from_40n_and_within_the_rig_ceiling() -> None:
    for target in CATALOG:
        assert target.dec_deg >= _MIN_DEC_DEG_FOR_40N_VISIBILITY, (
            f"{target.catalog_id} at dec {target.dec_deg} never gets high enough "
            "from 40N+"
        )
        assert target.magnitude <= _MAX_CATALOG_MAGNITUDE, (
            f"{target.catalog_id} (mag {target.magnitude}) is fainter than any "
            "rig in scope can reach"
        )


def test_no_alias_collides_with_another_targets_catalog_id_or_alias() -> None:
    """The whole point of aliases: a physical object with several catalog
    designations (e.g. M31 / NGC 224) must appear exactly once in CATALOG,
    not once per name it's known by.
    """
    all_ids = {target.catalog_id for target in CATALOG}
    all_aliases = [alias for target in CATALOG for alias in target.aliases]

    assert len(all_aliases) == len(set(all_aliases)), "duplicate alias across targets"
    assert all_ids.isdisjoint(all_aliases), "an alias duplicates a primary catalog_id"


def test_catalog_coordinates_are_within_valid_ranges() -> None:
    for target in CATALOG:
        assert 0.0 <= target.ra_deg < 360.0
        assert -90.0 <= target.dec_deg <= 90.0
        assert target.name


def test_catalog_magnitudes_and_sizes_are_populated() -> None:
    for target in CATALOG:
        assert target.magnitude < 99.0, f"{target.catalog_id} has no real magnitude"
        assert target.size_arcmin != (0.0, 0.0), (
            f"{target.catalog_id} has no known size"
        )


def test_all_bin_files_on_disk_are_covered_by_the_bounds_table() -> None:
    on_disk = {path.name for path in catalog._CATALOG_DIR.glob("mag_*.yaml")}
    assert on_disk == set(_BIN_BOUNDS)


@pytest.mark.parametrize("filename", list(_BIN_BOUNDS))
def test_bin_file_objects_fall_within_their_named_magnitude_range(
    filename: str,
) -> None:
    low, high = _BIN_BOUNDS[filename]
    raw_targets = yaml.safe_load(
        (catalog._CATALOG_DIR / filename).read_text(encoding="utf-8")
    )
    for raw in raw_targets:
        magnitude = raw["magnitude"]
        if low is not None:
            assert magnitude >= low, (
                f"{raw['catalog_id']} (mag {magnitude}) belongs below {filename}"
            )
        assert magnitude < high, (
            f"{raw['catalog_id']} (mag {magnitude}) belongs above {filename}"
        )


def test_load_catalog_parses_magnitude_size_and_aliases_from_a_bin_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "mag_lt_6.yaml").write_text(
        """
- name: "Test Object"
  catalog_id: "M999"
  aliases: ["NGC 999"]
  ra_deg: 10.0
  dec_deg: 20.0
  magnitude: 4.2
  size_arcmin: [5.0, 3.0]
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(catalog, "_CATALOG_DIR", tmp_path)

    targets = catalog._load_catalog()

    assert len(targets) == 1
    target = targets[0]
    assert target.catalog_id == "M999"
    assert target.aliases == ("NGC 999",)
    assert target.magnitude == pytest.approx(4.2)
    assert target.size_arcmin == (5.0, 3.0)


def test_load_catalog_picks_up_any_new_mag_bin_file_automatically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "mag_lt_6.yaml").write_text(
        '- {name: "A", catalog_id: "M901", ra_deg: 1.0, dec_deg: 1.0, magnitude: 5.0}',
        encoding="utf-8",
    )
    (tmp_path / "mag_20_21.yaml").write_text(
        '- {name: "B", catalog_id: "M902", ra_deg: 2.0, dec_deg: 2.0, magnitude: 20.5}',
        encoding="utf-8",
    )
    monkeypatch.setattr(catalog, "_CATALOG_DIR", tmp_path)

    targets = catalog._load_catalog()

    assert {target.catalog_id for target in targets} == {"M901", "M902"}

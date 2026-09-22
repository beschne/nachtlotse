from __future__ import annotations

from pathlib import Path
from typing import get_args

import pytest
import yaml

from nachtlotse.data import catalog
from nachtlotse.data.catalog import CATALOG
from nachtlotse.engine.models import TargetType

_VALID_TYPES = set(get_args(TargetType))

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
    "mag_13_14.yaml": (13.0, 14.0),
    "mag_15_16.yaml": (15.0, 16.0),
}

# The one bin file that isn't a numeric magnitude range: objects with no
# reliably sourced integrated magnitude at all (see SKIPPED-OBJECTS.md).
_UNKNOWN_MAGNITUDE_BIN_FILENAME = "mag_unknown.yaml"

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


def test_catalog_has_a_plausible_number_of_unique_objects() -> None:
    # 185 after the three book imports; growing block by block as
    # mag_unknown.yaml is populated from SKIPPED-OBJECTS.md (roadmap #1) —
    # wide enough to not need bumping every block, tight enough to still
    # catch a loader regression that silently drops or duplicates entries.
    assert 175 <= len(CATALOG) <= 260


def test_catalog_ids_are_unique() -> None:
    catalog_ids = [target.catalog_id for target in CATALOG]
    assert len(catalog_ids) == len(set(catalog_ids))
    assert all(catalog_id for catalog_id in catalog_ids), (
        "every target needs a real, citable catalog_id"
    )


def test_catalog_targets_are_visible_from_40n_and_within_the_rig_ceiling() -> None:
    for target in CATALOG:
        assert target.dec_deg >= _MIN_DEC_DEG_FOR_40N_VISIBILITY, (
            f"{target.catalog_id} at dec {target.dec_deg} never gets high enough "
            "from 40N+"
        )
        # A target with no known magnitude (mag_unknown.yaml) can't be
        # checked against the ceiling — that's exactly what's unknown
        # about it — so it's exempt rather than assumed too faint.
        if target.magnitude is not None:
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


def test_catalog_sizes_are_always_populated() -> None:
    """Unlike magnitude, size is never optional: it's what framing scores
    on, and it's the admission requirement for mag_unknown.yaml entries
    that have no magnitude to be checked against at all."""
    for target in CATALOG:
        assert target.size_arcmin != (0.0, 0.0), (
            f"{target.catalog_id} has no known size"
        )


def test_catalog_targets_carry_at_least_one_valid_type() -> None:
    for target in CATALOG:
        assert target.types, f"{target.catalog_id} has no types"
        assert set(target.types) <= _VALID_TYPES, (
            f"{target.catalog_id} has an unknown type in {target.types}"
        )


def test_all_bin_files_on_disk_are_covered_by_the_bounds_table() -> None:
    on_disk = {path.name for path in catalog._CATALOG_DIR.glob("mag_*.yaml")}
    assert on_disk == set(_BIN_BOUNDS) | {_UNKNOWN_MAGNITUDE_BIN_FILENAME}


def test_only_the_unknown_bin_file_omits_magnitude() -> None:
    """Bounds-checked bin files (mag_lt_6.yaml, etc.) always carry a real
    magnitude; mag_unknown.yaml is the one deliberate exception — this
    keeps "no magnitude" from silently sneaking into the wrong file."""
    for filename in _BIN_BOUNDS:
        raw_targets = yaml.safe_load(
            (catalog._CATALOG_DIR / filename).read_text(encoding="utf-8")
        )
        for raw in raw_targets:
            assert raw.get("magnitude") is not None, (
                f"{raw['catalog_id']} in {filename} has no magnitude — belongs in "
                f"{_UNKNOWN_MAGNITUDE_BIN_FILENAME} instead"
            )

    unknown_raw_targets = (
        yaml.safe_load(
            (catalog._CATALOG_DIR / _UNKNOWN_MAGNITUDE_BIN_FILENAME).read_text(
                encoding="utf-8"
            )
        )
        or []
    )
    for raw in unknown_raw_targets:
        assert raw.get("magnitude") is None, (
            f"{raw['catalog_id']} in {_UNKNOWN_MAGNITUDE_BIN_FILENAME} has a real "
            "magnitude — belongs in a numeric mag_*.yaml bin instead"
        )


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
  types: ["galaxy"]
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
    assert target.types == ("galaxy",)
    assert target.favorite is False


def test_load_catalog_parses_an_omitted_magnitude_as_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "mag_unknown.yaml").write_text(
        """
- name: "Test Nebula"
  catalog_id: "Sh2-999"
  ra_deg: 10.0
  dec_deg: 20.0
  size_arcmin: [30.0, 20.0]
  types: ["emission_nebula"]
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(catalog, "_CATALOG_DIR", tmp_path)

    (target,) = catalog._load_catalog()

    assert target.magnitude is None
    assert target.size_arcmin == (30.0, 20.0)


def test_load_catalog_ignores_an_inline_favorite_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Favorites are deliberately NOT read from the shared catalog YAML
    itself any more (see the module docstring) — a stray `favorite: true`
    left in a `mag_*.yaml` file must be silently ignored, not honored."""
    (tmp_path / "mag_10_11.yaml").write_text(
        """
- name: "Test Variable"
  catalog_id: "T Test"
  ra_deg: 10.0
  dec_deg: 20.0
  magnitude: 10.5
  size_arcmin: [0.05, 0.05]
  types: ["variable_star"]
  favorite: true
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(catalog, "_CATALOG_DIR", tmp_path)

    (target,) = catalog._load_catalog()

    assert target.favorite is False


def test_load_catalog_applies_local_favorites_by_catalog_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real mechanism: a `catalog_id` listed in the gitignored
    `favorites_local.yaml` next to the catalog package gets folded into
    that target's `favorite` field at load time; an unlisted target
    stays unstarred."""
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()
    (catalog_dir / "mag_10_11.yaml").write_text(
        """
- name: "Test Variable"
  catalog_id: "T Test"
  ra_deg: 10.0
  dec_deg: 20.0
  magnitude: 10.5
  size_arcmin: [0.05, 0.05]
  types: ["variable_star"]

- name: "Other Variable"
  catalog_id: "T Other"
  ra_deg: 30.0
  dec_deg: 40.0
  magnitude: 10.5
  size_arcmin: [0.05, 0.05]
  types: ["variable_star"]
""",
        encoding="utf-8",
    )
    (tmp_path / "favorites_local.yaml").write_text('- "T Test"\n', encoding="utf-8")
    monkeypatch.setattr(catalog, "_CATALOG_DIR", catalog_dir)

    starred, unstarred = catalog._load_catalog()

    assert starred.favorite is True
    assert unstarred.favorite is False


def test_catalog_contains_t_crb() -> None:
    """T CrB is favorites_local.template.yaml's real, shipped example
    (roadmap #1, "Favorites in the catalog") — a regression here means
    that example no longer points at a real catalog entry."""
    (t_crb,) = (target for target in CATALOG if target.catalog_id == "T CrB")
    assert t_crb.types == ("variable_star",)


def test_favorites_template_lists_only_t_crb() -> None:
    """`favorites_local.template.yaml` (committed, safe to ship — unlike
    `favorites_local.yaml` itself) documents the format with exactly the
    one example ROADMAP.md's "Favorites in the catalog" calls out."""
    template_path = catalog._CATALOG_DIR.parent / "favorites_local.template.yaml"
    favorite_ids = yaml.safe_load(template_path.read_text(encoding="utf-8")) or []
    assert favorite_ids == ["T CrB"]


def test_no_catalog_file_carries_an_inline_favorite_key() -> None:
    """Guards the module docstring's separation: favorites belong only in
    the local, gitignored favorites_local.yaml, never hand-added back
    into the shared, committed catalog data."""
    for path in catalog._CATALOG_DIR.glob("mag_*.yaml"):
        raw_targets = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for raw in raw_targets:
            assert "favorite" not in raw, (
                f"{raw.get('catalog_id')} in {path.name} carries an inline "
                "favorite key — move it to favorites_local.yaml instead"
            )


_BIN_ORDER = [*_BIN_BOUNDS, _UNKNOWN_MAGNITUDE_BIN_FILENAME]


def _expected_bin(magnitude: float | None) -> str:
    if magnitude is None:
        return _UNKNOWN_MAGNITUDE_BIN_FILENAME
    for filename, (low, high) in _BIN_BOUNDS.items():
        if (low is None or magnitude >= low) and magnitude < high:
            return filename
    raise AssertionError(f"magnitude {magnitude} matches no known bin")


def test_catalog_is_loaded_brightest_first() -> None:
    """`planning.rank_targets`'s `limit` caps evaluation to the first N
    entries of CATALOG, on the assumption that catalog order is
    brightest-first — a regression here (e.g. back to alphabetical glob
    order) would silently make `--limit 50` skip every bright, attractive
    object in favor of whichever bin sorts first by filename. Only bin-level
    order is asserted; a bin file's own internal ordering isn't a contract.
    """
    bin_ranks = [_BIN_ORDER.index(_expected_bin(target.magnitude)) for target in CATALOG]
    assert bin_ranks == sorted(bin_ranks)


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

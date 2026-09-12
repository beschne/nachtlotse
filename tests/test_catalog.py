from __future__ import annotations

from nachtlotse.data.catalog import MESSIER_CORE


def test_messier_core_has_around_thirty_unique_objects() -> None:
    assert 25 <= len(MESSIER_CORE) <= 35

    catalog_ids = [target.catalog_id for target in MESSIER_CORE]
    assert len(catalog_ids) == len(set(catalog_ids))
    assert all(catalog_id.startswith("M") for catalog_id in catalog_ids)


def test_messier_core_coordinates_are_within_valid_ranges() -> None:
    for target in MESSIER_CORE:
        assert 0.0 <= target.ra_deg < 360.0
        assert -90.0 <= target.dec_deg <= 90.0
        assert target.name

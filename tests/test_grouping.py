"""Multi-object grouping tests — see nachtlotse/engine/grouping.py."""

from __future__ import annotations

import pytest

from nachtlotse.engine import grouping
from nachtlotse.engine.models import Mount, Optics, Rig, Sensor, Target

_SENSOR = Sensor(name="Test Sensor", width_px=4000, height_px=3000, pixel_um=3.0)

RIG = Rig(
    name="Test Rig",
    optics=Optics(name="Test Optics", focal_length_mm=250.0, aperture_mm=50.0),
    sensor=_SENSOR,
    mount=Mount(name="EQ Test Mount", kind="eq"),
)

_FOV_SHORT_ARCMIN = min(RIG.fov_deg) * 60.0


def _target(name: str, ra_deg: float, dec_deg: float) -> Target:
    return Target(name=name, ra_deg=ra_deg, dec_deg=dec_deg)


def test_angular_separation_deg_along_the_celestial_equator_equals_the_ra_difference() -> (
    None
):
    # On dec=0, RA differences map directly onto a great circle — an exact,
    # independently known value rather than an approximation.
    a = _target("a", ra_deg=10.0, dec_deg=0.0)
    b = _target("b", ra_deg=11.5, dec_deg=0.0)

    assert grouping.angular_separation_deg(a, b) == pytest.approx(1.5, abs=1e-9)


def test_angular_separation_deg_is_symmetric() -> None:
    a = _target("a", ra_deg=200.0, dec_deg=45.0)
    b = _target("b", ra_deg=201.0, dec_deg=44.5)

    assert grouping.angular_separation_deg(a, b) == pytest.approx(
        grouping.angular_separation_deg(b, a)
    )


def test_group_span_arcmin_is_the_largest_pairwise_separation() -> None:
    close_a = _target("close a", ra_deg=10.0, dec_deg=0.0)
    close_b = _target("close b", ra_deg=10.1, dec_deg=0.0)
    far = _target("far", ra_deg=15.0, dec_deg=0.0)

    span_arcmin = grouping.group_span_arcmin([close_a, close_b, far])

    expected_arcmin = grouping.angular_separation_deg(close_a, far) * 60.0
    assert span_arcmin == pytest.approx(expected_arcmin)


def test_group_span_arcmin_is_zero_for_fewer_than_two_targets() -> None:
    assert grouping.group_span_arcmin([]) == 0.0
    assert grouping.group_span_arcmin([_target("solo", ra_deg=0.0, dec_deg=0.0)]) == 0.0


def test_co_visible_group_is_true_within_the_fov_short_side_false_beyond_it() -> None:
    origin = _target("origin", ra_deg=10.0, dec_deg=0.0)
    within = _target(
        "within", ra_deg=10.0 + (_FOV_SHORT_ARCMIN * 0.5) / 60.0, dec_deg=0.0
    )
    beyond = _target(
        "beyond", ra_deg=10.0 + (_FOV_SHORT_ARCMIN * 2.0) / 60.0, dec_deg=0.0
    )

    assert grouping.co_visible_group(RIG, [origin, within]) is True
    assert grouping.co_visible_group(RIG, [origin, beyond]) is False


def test_co_visible_group_is_true_for_a_single_target() -> None:
    assert grouping.co_visible_group(RIG, [_target("solo", ra_deg=0.0, dec_deg=0.0)])


def test_group_framing_score_is_full_when_the_span_exactly_fills_the_frame() -> None:
    origin = _target("origin", ra_deg=10.0, dec_deg=0.0)
    edge = _target("edge", ra_deg=10.0 + _FOV_SHORT_ARCMIN / 60.0, dec_deg=0.0)

    assert grouping.group_framing_score(RIG, [origin, edge]) == pytest.approx(1.0)


def test_find_groups_clusters_close_targets_and_leaves_far_ones_alone() -> None:
    # A close pair, a close triple, and one lone target far from everything.
    pair_a = _target("pair a", ra_deg=10.0, dec_deg=0.0)
    pair_b = _target(
        "pair b", ra_deg=10.0 + (_FOV_SHORT_ARCMIN * 0.3) / 60.0, dec_deg=0.0
    )
    triple_a = _target("triple a", ra_deg=100.0, dec_deg=20.0)
    triple_b = _target(
        "triple b", ra_deg=100.0 + (_FOV_SHORT_ARCMIN * 0.2) / 60.0, dec_deg=20.0
    )
    triple_c = _target(
        "triple c", ra_deg=100.0 - (_FOV_SHORT_ARCMIN * 0.2) / 60.0, dec_deg=20.0
    )
    lone = _target("lone", ra_deg=200.0, dec_deg=-10.0)

    groups = grouping.find_groups(
        RIG, [pair_a, pair_b, triple_a, triple_b, triple_c, lone]
    )

    grouped_names = {frozenset(t.name for t in group) for group in groups}
    assert grouped_names == {
        frozenset({"pair a", "pair b"}),
        frozenset({"triple a", "triple b", "triple c"}),
    }


def test_find_groups_returns_nothing_when_no_candidates_are_co_visible() -> None:
    scattered = [
        _target("first", ra_deg=0.0, dec_deg=0.0),
        _target("second", ra_deg=90.0, dec_deg=0.0),
        _target("third", ra_deg=180.0, dec_deg=0.0),
    ]

    assert grouping.find_groups(RIG, scattered) == []


def test_centroid_target_sits_at_the_geometric_mean_of_a_symmetric_pair() -> None:
    # Compared via angular separation, not raw ra_deg/dec_deg equality —
    # 0 and 360 are the same point, so that's the only representation-safe
    # way to check "is the centroid where we expect it to be".
    a = _target("a", ra_deg=10.0, dec_deg=0.0)
    b = _target("b", ra_deg=12.0, dec_deg=0.0)
    expected = _target("expected", ra_deg=11.0, dec_deg=0.0)

    centroid = grouping.centroid_target([a, b])

    assert grouping.angular_separation_deg(centroid, expected) == pytest.approx(
        0.0, abs=1e-6
    )


def test_centroid_target_handles_the_ra_zero_wraparound() -> None:
    # Two points straddling RA 0/360 average to RA ~0, not RA 180 — a plain
    # arithmetic mean of 359 and 1 would get this backwards.
    a = _target("a", ra_deg=359.0, dec_deg=0.0)
    b = _target("b", ra_deg=1.0, dec_deg=0.0)
    expected = _target("expected", ra_deg=0.0, dec_deg=0.0)

    centroid = grouping.centroid_target([a, b])

    assert grouping.angular_separation_deg(centroid, expected) == pytest.approx(
        0.0, abs=1e-6
    )

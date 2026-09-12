"""Framing-score and field-rotation tests (M3 DoD).

Field-rotation expectations are calibrated numerically against astroplan's
own `parallactic_angle` (see the derivation in the session that introduced
this module) rather than assumed: a target whose transit passes within a
degree of the zenith shows a rate roughly two orders of magnitude higher
than one 30° away, at this project's latitudes.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from astropy.time import Time

from nachtlotse.engine import framing
from nachtlotse.engine.constraints import build_fixed_target, build_observer
from nachtlotse.engine.models import (
    HorizonProfile,
    Mount,
    Optics,
    Rig,
    Sensor,
    Site,
    Target,
)

SITE = Site(
    name="Bad Homburg",
    lat_deg=50.2266,
    lon_deg=8.6180,
    elevation_m=190.0,
    tz="Europe/Berlin",
    horizon=HorizonProfile(points=[]),
)

_SENSOR = Sensor(name="Test Sensor", width_px=4000, height_px=3000, pixel_um=3.0)

ALTAZ_RIG = Rig(
    name="Alt-Az Test Rig",
    optics=Optics(name="Test Optics", focal_length_mm=250.0, aperture_mm=50.0),
    sensor=_SENSOR,
    mount=Mount(name="Alt-Az Test Mount", kind="altaz"),
)

EQ_RIG = Rig(
    name="EQ Test Rig",
    optics=Optics(name="Test Optics", focal_length_mm=250.0, aperture_mm=50.0),
    sensor=_SENSOR,
    mount=Mount(name="EQ Test Mount", kind="eq"),
)


# A reference known to fall within an astronomical-twilight dark window at
# SITE (established in test_constraints.py) — transits are anchored here so
# they land at night, not just "close to the given RA/dec at some hour".
_NIGHT_REFERENCE = datetime(2026, 9, 12, 22, 0, tzinfo=UTC)


def _transit_time(dec_deg: float) -> tuple[Target, datetime]:
    """A target whose RA matches the LST at `_NIGHT_REFERENCE` (so it
    transits close to that already-nighttime moment), refined via
    astroplan's own transit finder.
    """
    observer = build_observer(SITE)
    lst_deg = (
        Time(_NIGHT_REFERENCE)
        .sidereal_time("apparent", longitude=observer.location.lon)
        .deg
    )
    target = Target(name="transit-finder", ra_deg=lst_deg, dec_deg=dec_deg)
    fixed_target = build_fixed_target(target)
    t_transit = observer.target_meridian_transit_time(
        Time(_NIGHT_REFERENCE), fixed_target, which="nearest"
    )
    return target, t_transit.to_datetime(timezone=UTC)


NEAR_ZENITH_TARGET, NEAR_ZENITH_TRANSIT = _transit_time(SITE.lat_deg - 0.5)
FAR_FROM_ZENITH_TARGET, FAR_FROM_ZENITH_TRANSIT = _transit_time(SITE.lat_deg - 30.0)


def test_field_rotation_rate_is_much_higher_near_the_zenith() -> None:
    near_rate = framing.field_rotation_rate_deg_per_min(
        SITE, NEAR_ZENITH_TARGET, NEAR_ZENITH_TRANSIT
    )
    far_rate = framing.field_rotation_rate_deg_per_min(
        SITE, FAR_FROM_ZENITH_TARGET, FAR_FROM_ZENITH_TRANSIT
    )

    assert near_rate > far_rate * 10
    assert near_rate > framing.DEFAULT_MAX_ROTATION_RATE_DEG_PER_MIN
    assert far_rate < framing.DEFAULT_MAX_ROTATION_RATE_DEG_PER_MIN


def test_has_safe_field_rotation_rejects_near_zenith_transit_for_altaz_mount() -> None:
    assert (
        framing.has_safe_field_rotation(
            ALTAZ_RIG, SITE, NEAR_ZENITH_TARGET, NEAR_ZENITH_TRANSIT
        )
        is False
    )


def test_has_safe_field_rotation_accepts_far_from_zenith_transit_for_altaz_mount() -> (
    None
):
    assert (
        framing.has_safe_field_rotation(
            ALTAZ_RIG, SITE, FAR_FROM_ZENITH_TARGET, FAR_FROM_ZENITH_TRANSIT
        )
        is True
    )


def test_has_safe_field_rotation_is_always_true_for_eq_mount() -> None:
    """Eq mounts don't have this problem at all, regardless of zenith
    proximity — the rate isn't even computed for them."""
    assert (
        framing.has_safe_field_rotation(
            EQ_RIG, SITE, NEAR_ZENITH_TARGET, NEAR_ZENITH_TRANSIT
        )
        is True
    )


def test_framing_score_is_full_for_a_well_matched_target() -> None:
    # ALTAZ_RIG FoV short side; a target filling ~50% of it should score 1.0.
    fov_width_deg, fov_height_deg = ALTAZ_RIG.fov_deg
    fov_short_arcmin = min(fov_width_deg, fov_height_deg) * 60.0
    target = Target(
        name="well-matched",
        ra_deg=0.0,
        dec_deg=0.0,
        size_arcmin=(fov_short_arcmin * 0.5, fov_short_arcmin * 0.3),
    )
    assert framing.framing_score(ALTAZ_RIG, target) == pytest.approx(1.0)


def test_framing_score_penalizes_a_target_lost_in_the_frame() -> None:
    fov_width_deg, fov_height_deg = ALTAZ_RIG.fov_deg
    fov_short_arcmin = min(fov_width_deg, fov_height_deg) * 60.0
    tiny_target = Target(
        name="tiny",
        ra_deg=0.0,
        dec_deg=0.0,
        size_arcmin=(fov_short_arcmin * 0.01, fov_short_arcmin * 0.01),
    )
    assert 0.0 < framing.framing_score(ALTAZ_RIG, tiny_target) < 0.2


def test_framing_score_penalizes_a_clipped_oversized_target() -> None:
    fov_width_deg, fov_height_deg = ALTAZ_RIG.fov_deg
    fov_short_arcmin = min(fov_width_deg, fov_height_deg) * 60.0
    huge_target = Target(
        name="huge",
        ra_deg=0.0,
        dec_deg=0.0,
        size_arcmin=(fov_short_arcmin * 3.0, fov_short_arcmin * 3.0),
    )
    assert framing.framing_score(ALTAZ_RIG, huge_target) < 0.5


def test_framing_score_treats_unknown_size_as_unconstrained() -> None:
    unknown_size_target = Target(name="unknown", ra_deg=0.0, dec_deg=0.0)
    assert unknown_size_target.size_arcmin == (0.0, 0.0)
    assert framing.framing_score(ALTAZ_RIG, unknown_size_target) == pytest.approx(1.0)


def test_photographic_limiting_magnitude_matches_hand_calculation_for_30mm() -> None:
    # 2.7 + 5*log10(30) + 7.0 + (7.3 - 6.9) = 17.49 at Bortle 2
    assert framing.photographic_limiting_magnitude(30.0, 2.0) == pytest.approx(
        17.49, abs=0.01
    )
    # 2.7 + 5*log10(30) + 7.0 + (5.8 - 6.9) = 15.99 at Bortle 5
    assert framing.photographic_limiting_magnitude(30.0, 5.0) == pytest.approx(
        15.99, abs=0.01
    )


def test_photographic_limiting_magnitude_increases_with_aperture() -> None:
    small = framing.photographic_limiting_magnitude(30.0, 4.0)
    large = framing.photographic_limiting_magnitude(51.0, 4.0)
    assert large > small


def test_photographic_limiting_magnitude_increases_in_darker_skies() -> None:
    """Lower Bortle number = darker sky = fainter (higher) reachable magnitude."""
    dark = framing.photographic_limiting_magnitude(50.0, 2.0)
    bright = framing.photographic_limiting_magnitude(50.0, 7.0)
    assert dark > bright


def test_photographic_limiting_magnitude_interpolates_fractional_bortle_classes() -> (
    None
):
    at_four = framing.photographic_limiting_magnitude(50.0, 4.0)
    at_five = framing.photographic_limiting_magnitude(50.0, 5.0)
    at_four_and_a_half = framing.photographic_limiting_magnitude(50.0, 4.5)

    assert at_five < at_four_and_a_half < at_four


def test_photographic_limiting_magnitude_clamps_bortle_class_to_the_valid_range() -> (
    None
):
    assert framing.photographic_limiting_magnitude(50.0, 0.0) == pytest.approx(
        framing.photographic_limiting_magnitude(50.0, 1.0)
    )
    assert framing.photographic_limiting_magnitude(50.0, 12.0) == pytest.approx(
        framing.photographic_limiting_magnitude(50.0, 9.0)
    )

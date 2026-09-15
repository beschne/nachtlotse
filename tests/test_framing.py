"""Framing-score and field-rotation tests (M3 DoD).

Field-rotation expectations are calibrated numerically against astroplan's
own `parallactic_angle` (see the derivation in the session that introduced
this module) rather than assumed: a target whose transit passes within a
degree of the zenith shows a rate roughly two orders of magnitude higher
than one 30° away, at this project's latitudes.
"""

from __future__ import annotations

from dataclasses import replace
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


def test_target_priority_score_reduces_to_altitude_when_fit_is_full() -> None:
    assert framing.target_priority_score(45.0, 1.0) == pytest.approx(45.0 / 90.0)
    assert framing.target_priority_score(90.0, 1.0) == pytest.approx(1.0)


def test_target_priority_score_lets_a_poor_fit_veto_a_high_altitude() -> None:
    """The real-world case this exists for: a tiny planetary nebula near
    the zenith (fit ~0.02) must rank below a well-framed target lower in
    the sky, not above it just for having the higher raw altitude.
    """
    tiny_near_zenith = framing.target_priority_score(alt_deg=89.0, fit=0.02)
    well_framed_lower = framing.target_priority_score(alt_deg=45.0, fit=1.0)

    assert tiny_near_zenith < well_framed_lower


def test_target_priority_score_is_zero_for_a_target_that_does_not_fit_at_all() -> None:
    assert framing.target_priority_score(90.0, 0.0) == pytest.approx(0.0)


def test_target_priority_score_defaults_reach_to_unconstrained() -> None:
    assert framing.target_priority_score(45.0, 1.0) == pytest.approx(
        framing.target_priority_score(45.0, 1.0, 1.0)
    )


def test_target_priority_score_lets_a_poor_reach_downgrade_a_high_altitude() -> None:
    diffuse_but_high = framing.target_priority_score(alt_deg=89.0, fit=1.0, reach=0.2)
    well_reached_lower = framing.target_priority_score(alt_deg=45.0, fit=1.0, reach=1.0)

    assert diffuse_but_high < well_reached_lower


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


def test_sky_brightness_prefers_a_real_measurement_over_the_bortle_estimate() -> None:
    site = replace(SITE, bortle_class=8.0, zenith_sky_brightness_mag_arcsec2=21.2)
    assert framing.sky_brightness_mag_arcsec2(site) == pytest.approx(21.2)


def test_sky_brightness_falls_back_to_the_bortle_estimate_without_a_measurement() -> (
    None
):
    site = replace(SITE, bortle_class=4.0, zenith_sky_brightness_mag_arcsec2=None)
    assert framing.sky_brightness_mag_arcsec2(site) == pytest.approx(21.0)


def test_sky_brightness_is_none_without_either_a_measurement_or_a_bortle_class() -> (
    None
):
    site = replace(SITE, bortle_class=None, zenith_sky_brightness_mag_arcsec2=None)
    assert framing.sky_brightness_mag_arcsec2(site) is None


def test_sky_brightness_interpolates_fractional_bortle_classes() -> None:
    at_four = framing.sky_brightness_mag_arcsec2(replace(SITE, bortle_class=4.0))
    at_five = framing.sky_brightness_mag_arcsec2(replace(SITE, bortle_class=5.0))
    at_four_and_a_half = framing.sky_brightness_mag_arcsec2(
        replace(SITE, bortle_class=4.5)
    )

    assert at_five < at_four_and_a_half < at_four


def test_sky_brightness_decreases_at_higher_bortle_classes() -> None:
    """Higher Bortle number = brighter sky = lower (worse) mag/arcsec²."""
    dark = framing.sky_brightness_mag_arcsec2(replace(SITE, bortle_class=1.0))
    bright = framing.sky_brightness_mag_arcsec2(replace(SITE, bortle_class=9.0))
    assert dark > bright


def test_surface_brightness_matches_hand_calculation_for_m57() -> None:
    # mu = 8.8 + 2.5*log10(pi * 0.7 * 0.5 * 3600) ~= 17.79 (published ~18.1)
    assert framing.surface_brightness_mag_arcsec2(8.8, (1.4, 1.0)) == pytest.approx(
        17.79, abs=0.01
    )


def test_surface_brightness_matches_hand_calculation_for_ngc7000() -> None:
    # mu = 4.0 + 2.5*log10(pi * 60 * 50 * 3600) ~= 22.83 (published ~22)
    assert framing.surface_brightness_mag_arcsec2(4.0, (120.0, 100.0)) == pytest.approx(
        22.83, abs=0.01
    )


def test_surface_brightness_is_fainter_for_a_larger_object_at_the_same_magnitude() -> (
    None
):
    """The whole point of surface brightness over integrated magnitude:
    smearing the same total light over more area reads as fainter per
    pixel, even though the integrated magnitude is identical."""
    small = framing.surface_brightness_mag_arcsec2(8.0, (2.0, 2.0))
    large = framing.surface_brightness_mag_arcsec2(8.0, (20.0, 20.0))
    assert large > small


def test_reach_factor_is_unconstrained_without_a_magnitude() -> None:
    site = replace(SITE, bortle_class=8.0)
    assert framing.reach_factor(site, None, (30.0, 20.0)) == pytest.approx(1.0)


def test_reach_factor_is_unconstrained_without_a_known_size() -> None:
    site = replace(SITE, bortle_class=8.0)
    assert framing.reach_factor(site, 15.0, (0.0, 0.0)) == pytest.approx(1.0)


def test_reach_factor_is_unconstrained_without_documented_sky_brightness() -> None:
    site = replace(SITE, bortle_class=None, zenith_sky_brightness_mag_arcsec2=None)
    assert framing.reach_factor(site, 15.0, (200.0, 200.0)) == pytest.approx(1.0)


def test_reach_factor_is_full_for_a_compact_bright_target_at_any_site() -> None:
    """M57: small and bright enough that surface brightness never
    approaches even a bright site's reachable limit."""
    bright_site = replace(SITE, bortle_class=9.0)
    assert framing.reach_factor(bright_site, 8.8, (1.4, 1.0)) == pytest.approx(1.0)


def test_reach_factor_downgrades_a_diffuse_target_under_a_bright_sky() -> None:
    """NGC 7000 at Bortle 8 (~17.5 mag/arcsec² estimated sky brightness):
    a real, partial downgrade — neither unconstrained nor at the floor."""
    bright_site = replace(SITE, bortle_class=8.0)
    reach = framing.reach_factor(bright_site, 4.0, (120.0, 100.0))
    assert framing._REACH_FLOOR < reach < 1.0


def test_reach_factor_never_drops_below_its_floor() -> None:
    """A deliberately absurd case (very faint, very large) still never
    hits zero — reach downgrades, it never excludes outright."""
    bright_site = replace(SITE, bortle_class=9.0)
    reach = framing.reach_factor(bright_site, 15.0, (200.0, 200.0))
    assert reach == pytest.approx(framing._REACH_FLOOR)


def test_reach_factor_improves_at_a_darker_site() -> None:
    target_magnitude, target_size = 4.0, (120.0, 100.0)
    dark_site = replace(SITE, bortle_class=2.0)
    bright_site = replace(SITE, bortle_class=8.0)

    dark_reach = framing.reach_factor(dark_site, target_magnitude, target_size)
    bright_reach = framing.reach_factor(bright_site, target_magnitude, target_size)
    assert dark_reach > bright_reach

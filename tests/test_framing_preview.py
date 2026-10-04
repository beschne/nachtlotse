"""Framing-preview geometry tests (ROADMAP #1, step 1).

Expectations come from independent derivations rather than the module's
own formulas: tangent-plane offsets are checked against astropy's
`spherical_offsets_to`, and the alt-az frame angle (computed by astropy
frame transforms) against the textbook parallactic-angle formula
evaluated on apparent (TETE) coordinates and apparent sidereal time —
and, away from the zenith, against astroplan's own `parallactic_angle`.
"""

from __future__ import annotations

import itertools
import math
from datetime import UTC, datetime, timedelta

import pytest
from astropy import units as u
from astropy.coordinates import TETE, SkyCoord
from astropy.time import Time

from nachtlotse.engine import constraints, framing, framing_preview, grouping
from nachtlotse.engine.constraints import build_fixed_target, build_observer
from nachtlotse.engine.models import Target
from tests.test_framing import ALTAZ_RIG, EQ_RIG, SITE

# Catalog values (data/catalog/mag_lt_6.yaml, mag_8_9.yaml).
M31 = Target(
    name="Andromeda Galaxy",
    catalog_id="M31",
    ra_deg=10.6847,
    dec_deg=41.2692,
    size_arcmin=(190.0, 60.0),
)
M32 = Target(
    name="M32",
    catalog_id="M32",
    ra_deg=10.674,
    dec_deg=40.865,
    size_arcmin=(7.74, 4.86),
)
M110 = Target(
    name="M110",
    catalog_id="M110",
    ra_deg=10.092,
    dec_deg=41.685,
    size_arcmin=(16.22, 9.59),
)
M42 = Target(name="Orion Nebula", catalog_id="M42", ra_deg=83.82, dec_deg=-5.39)

# M31 well up in the east, before its transit (~00:30 UTC in mid-September).
WHEN = datetime(2026, 9, 12, 21, 0, tzinfo=UTC)


def _analytic_parallactic_angle_deg(target: Target, when: datetime) -> float:
    """q = atan2(sin H, tan(lat) cos(dec) - sin(dec) cos(H)), on the
    target's apparent (true-equator, true-equinox) place and the apparent
    local sidereal time. Measured against the true-of-date north, which
    differs from ICRS north by ~0.05-0.15 deg at these dates (precession
    since J2000) — hence the tolerances below."""
    observer = build_observer(SITE)
    t = Time(when)
    apparent = build_fixed_target(target).coord.transform_to(
        TETE(obstime=t, location=observer.location)
    )
    lst = t.sidereal_time("apparent", longitude=observer.location.lon)
    hour_angle = math.radians((lst - apparent.ra).wrap_at(180 * u.deg).deg)
    dec = apparent.dec.rad
    lat = math.radians(SITE.lat_deg)
    return math.degrees(
        math.atan2(
            math.sin(hour_angle),
            math.tan(lat) * math.cos(dec) - math.sin(dec) * math.cos(hour_angle),
        )
    )


def _wrap(angle_deg: float) -> float:
    return (angle_deg + 180.0) % 360.0 - 180.0


# --- tangent-plane projection -------------------------------------------


def test_gnomonic_offset_of_the_center_is_zero() -> None:
    assert framing_preview.gnomonic_offset_arcmin(10.0, 40.0, 10.0, 40.0) == (
        pytest.approx(0.0, abs=1e-9),
        pytest.approx(0.0, abs=1e-9),
    )


def test_gnomonic_offset_matches_astropy_for_m32_around_m31() -> None:
    east, north = framing_preview.gnomonic_offset_arcmin(
        M31.ra_deg, M31.dec_deg, M32.ra_deg, M32.dec_deg
    )
    center = SkyCoord(ra=M31.ra_deg * u.deg, dec=M31.dec_deg * u.deg)
    other = SkyCoord(ra=M32.ra_deg * u.deg, dec=M32.dec_deg * u.deg)
    d_east, d_north = center.spherical_offsets_to(other)

    assert east == pytest.approx(d_east.to(u.arcmin).value, abs=0.01)
    assert north == pytest.approx(d_north.to(u.arcmin).value, abs=0.01)
    # M32 sits ~24' south of M31's core, barely offset in RA.
    assert north == pytest.approx(-24.2, abs=0.2)


def test_gnomonic_offset_east_is_positive_for_larger_ra() -> None:
    east, north = framing_preview.gnomonic_offset_arcmin(100.0, 0.0, 101.0, 0.0)
    assert east == pytest.approx(60.0, abs=0.05)
    assert north == pytest.approx(0.0, abs=1e-9)


def test_gnomonic_offset_is_none_on_the_far_hemisphere() -> None:
    assert framing_preview.gnomonic_offset_arcmin(0.0, 0.0, 180.0, 0.0) is None


# --- frame orientation ----------------------------------------------------


@pytest.mark.parametrize("hours_from_when", [0.0, 3.5, 6.0])
def test_altaz_frame_angle_matches_the_analytic_parallactic_angle(
    hours_from_when: float,
) -> None:
    """3.5 h lands near M31's transit at ~81 deg altitude, where the angle
    changes fastest — the case astroplan's J2000 shortcut gets wrong."""
    when = WHEN + timedelta(hours=hours_from_when)
    angle = framing_preview.frame_angle_deg(ALTAZ_RIG, SITE, M31, when)
    expected = _analytic_parallactic_angle_deg(M31, when)
    assert _wrap(angle - expected) == pytest.approx(0.0, abs=0.2)


def test_altaz_frame_angle_matches_astroplan_away_from_the_zenith() -> None:
    angle = framing_preview.frame_angle_deg(ALTAZ_RIG, SITE, M31, WHEN)
    astroplan_q = (
        build_observer(SITE).parallactic_angle(Time(WHEN), build_fixed_target(M31)).deg
    )
    assert _wrap(angle - astroplan_q) == pytest.approx(0.0, abs=0.5)


def test_altaz_frame_angle_is_zero_at_transit_south_of_the_zenith() -> None:
    observer = build_observer(SITE)
    transit = observer.target_meridian_transit_time(
        Time(WHEN), build_fixed_target(M42), which="next"
    ).to_datetime(timezone=UTC)
    angle = framing_preview.frame_angle_deg(ALTAZ_RIG, SITE, M42, transit)
    # Not exactly 0: the true-of-date meridian is tilted against ICRS
    # north by precession (~0.15 deg at M42's RA in 2026).
    assert angle == pytest.approx(0.0, abs=0.3)


def test_altaz_frame_angle_sign_flips_across_the_meridian() -> None:
    """East of the meridian the zenith lies to the west of the target
    (negative position angle), west of it to the east (positive)."""
    rising = framing_preview.frame_angle_deg(ALTAZ_RIG, SITE, M31, WHEN)
    setting = framing_preview.frame_angle_deg(
        ALTAZ_RIG, SITE, M31, WHEN + timedelta(hours=6)
    )
    assert rising < 0.0 < setting


def test_eq_frame_angle_is_zero() -> None:
    assert framing_preview.frame_angle_deg(EQ_RIG, SITE, M31, WHEN) == 0.0


# --- frame rectangle ------------------------------------------------------


def test_frame_corners_unrotated_put_the_width_along_east_west() -> None:
    corners = framing_preview.frame_corners(120.0, 80.0, 0.0)
    easts = [c[0] for c in corners]
    norths = [c[1] for c in corners]
    assert max(easts) - min(easts) == pytest.approx(120.0)
    assert max(norths) - min(norths) == pytest.approx(80.0)


def test_frame_corners_rotated_90_put_the_width_along_north_south() -> None:
    corners = framing_preview.frame_corners(120.0, 80.0, 90.0)
    easts = [c[0] for c in corners]
    norths = [c[1] for c in corners]
    assert max(easts) - min(easts) == pytest.approx(80.0)
    assert max(norths) - min(norths) == pytest.approx(120.0)


# --- full preview ---------------------------------------------------------


def test_preview_matches_the_rigs_fov_and_framing_score() -> None:
    preview = framing_preview.framing_preview(SITE, ALTAZ_RIG, [M31], WHEN)

    fov_width_deg, fov_height_deg = ALTAZ_RIG.fov_deg
    assert preview.fov_width_arcmin == pytest.approx(fov_width_deg * 60.0)
    assert preview.fov_height_arcmin == pytest.approx(fov_height_deg * 60.0)
    assert preview.span_arcmin == 190.0
    assert preview.fill_fraction == pytest.approx(
        190.0 / framing.fov_short_arcmin(ALTAZ_RIG)
    )
    assert preview.fit == framing.framing_score(ALTAZ_RIG, M31)
    assert (preview.center_ra_deg, preview.center_dec_deg) == (
        M31.ra_deg,
        M31.dec_deg,
    )


def test_preview_reports_rotation_rate_only_for_altaz() -> None:
    altaz = framing_preview.framing_preview(SITE, ALTAZ_RIG, [M31], WHEN)
    eq = framing_preview.framing_preview(SITE, EQ_RIG, [M31], WHEN)

    assert altaz.rotation_rate_deg_per_min == pytest.approx(
        framing.field_rotation_rate_deg_per_min(SITE, M31, WHEN)
    )
    assert eq.rotation_rate_deg_per_min is None
    assert eq.frame_angle_deg == 0.0


def test_preview_includes_neighbors_inside_the_frame_only() -> None:
    preview = framing_preview.framing_preview(
        SITE, ALTAZ_RIG, [M31], WHEN, neighbors=[M31, M32, M110, M42]
    )
    by_id = {obj.target.catalog_id: obj for obj in preview.objects}

    assert set(by_id) == {"M31", "M32", "M110"}
    assert by_id["M31"].primary is True
    assert (by_id["M31"].east_arcmin, by_id["M31"].north_arcmin) == (0.0, 0.0)
    assert by_id["M32"].primary is False
    assert by_id["M110"].primary is False


def test_preview_of_a_group_centers_on_its_centroid_and_scores_its_span() -> None:
    group = (M31, M110)
    preview = framing_preview.framing_preview(SITE, ALTAZ_RIG, group, WHEN)
    centroid = grouping.centroid_target(group)

    assert preview.center_ra_deg == pytest.approx(centroid.ra_deg)
    assert preview.center_dec_deg == pytest.approx(centroid.dec_deg)
    assert preview.span_arcmin == pytest.approx(grouping.group_span_arcmin(group))
    assert preview.fit == pytest.approx(grouping.group_framing_score(ALTAZ_RIG, group))
    assert all(obj.primary for obj in preview.objects)
    # Two members, symmetric about the centroid.
    east_sum = sum(obj.east_arcmin for obj in preview.objects)
    north_sum = sum(obj.north_arcmin for obj in preview.objects)
    assert east_sum == pytest.approx(0.0, abs=0.01)
    assert north_sum == pytest.approx(0.0, abs=0.01)


def test_preview_with_unknown_size_has_no_fill_fraction() -> None:
    preview = framing_preview.framing_preview(SITE, ALTAZ_RIG, [M42], WHEN)
    assert preview.span_arcmin == 0.0
    assert preview.fill_fraction is None
    assert preview.fit == 1.0
    assert preview.objects[0].size_known is False


def test_preview_needs_at_least_one_target() -> None:
    with pytest.raises(ValueError):
        framing_preview.framing_preview(SITE, ALTAZ_RIG, [], WHEN)


# --- orientation through the night ----------------------------------------

NIGHT = constraints.dark_window(SITE, datetime(2026, 9, 12, 12, 0, tzinfo=UTC))


def test_orientation_track_samples_full_hours_inside_the_night() -> None:
    track = framing_preview.orientation_track(ALTAZ_RIG, SITE, M31, *NIGHT)

    assert len(track) >= 6  # M31 is up most of a September night
    for orientation in track:
        assert NIGHT[0] <= orientation.when <= NIGHT[1]
        assert (orientation.when.minute, orientation.when.second) == (0, 0)
        assert orientation.frame_angle_deg == pytest.approx(
            framing_preview.frame_angle_deg(ALTAZ_RIG, SITE, M31, orientation.when)
        )
    hours = [o.when for o in track]
    assert all(b - a == timedelta(hours=1) for a, b in itertools.pairwise(hours))


def test_orientation_track_skips_hours_below_the_minimum_altitude() -> None:
    full = framing_preview.orientation_track(
        ALTAZ_RIG, SITE, M42, *NIGHT, min_alt_deg=-90.0
    )
    gated = framing_preview.orientation_track(ALTAZ_RIG, SITE, M42, *NIGHT)

    # M42 only rises late on a September night: the gate drops the early hours.
    assert len(gated) < len(full)
    assert all(o.alt_deg >= constraints.DEFAULT_MIN_ALT_DEG for o in gated)


def test_orientation_track_is_empty_for_an_eq_mount() -> None:
    assert framing_preview.orientation_track(EQ_RIG, SITE, M31, *NIGHT) == ()


def test_preview_carries_the_track_only_when_given_a_night() -> None:
    assert (
        framing_preview.framing_preview(SITE, ALTAZ_RIG, [M31], WHEN).orientation_track
        == ()
    )
    with_night = framing_preview.framing_preview(
        SITE, ALTAZ_RIG, [M31], WHEN, night=NIGHT
    )
    assert with_night.orientation_track == framing_preview.orientation_track(
        ALTAZ_RIG, SITE, M31, *NIGHT
    )

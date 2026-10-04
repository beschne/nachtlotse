"""Comet positions and comet targets (ROADMAP.md: current events, step 1).

Known values come from two independent references, both queried for
2026-10-04 00:00 UT from Bad Homburg (8.618°E, 50.2266°N, 190 m):

- JPL Horizons (observer table, ICRF astrometric RA/Dec, r, delta), with
  JPL's own orbit solutions (10P: JPL#K265/56; C/2025 R3: JPL#33).
- The MPC Ephemeris Service, which for 10P/Tempel gave the same position
  to 0.1" (22 50 24.7, -33 10 44; delta 0.686, r 1.562) and a sky motion
  of 0.69"/min.

The orbits below are copied from the MPC's CometEls.txt as published on
2026-10-04 (epoch 2026-10-03). Two-body propagation from them lands within
~10" of both references — far below anything ranking or framing needs.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord

from nachtlotse.engine import comets, ephemeris
from nachtlotse.engine.models import CometOrbit, HorizonProfile, Site

BAD_HOMBURG = Site(
    name="Bad Homburg",
    lat_deg=50.2266,
    lon_deg=8.6180,
    elevation_m=190.0,
    tz="Europe/Berlin",
    horizon=HorizonProfile(points=[]),
)
WHEN = datetime(2026, 10, 4, 0, 0, tzinfo=UTC)

# CometEls.txt: "0010P  2026 08  2.1040  1.417739  0.537442  195.4604
# 117.7968   12.0271  20261003  13.1  4.0  10P/Tempel"
TEMPEL_2 = CometOrbit(
    designation="10P/Tempel",
    perihelion_year=2026,
    perihelion_month=8,
    perihelion_day=2.1040,
    perihelion_distance_au=1.417739,
    eccentricity=0.537442,
    argument_of_perihelion_deg=195.4604,
    longitude_of_ascending_node_deg=117.7968,
    inclination_deg=12.0271,
)

# CometEls.txt: "CK25R030  2026 04 19.8921  0.498613  1.000340  162.2277
# 38.7003  124.7300  20261003  12.2  4.0  C/2025 R3 (PANSTARRS)" — a
# hyperbolic orbit (e > 1), a separate branch of the orbit setup.
PANSTARRS_R3 = CometOrbit(
    designation="C/2025 R3 (PANSTARRS)",
    perihelion_year=2026,
    perihelion_month=4,
    perihelion_day=19.8921,
    perihelion_distance_au=0.498613,
    eccentricity=1.000340,
    argument_of_perihelion_deg=162.2277,
    longitude_of_ascending_node_deg=38.7003,
    inclination_deg=124.7300,
)


def _hms_dms(ra: str, dec: str) -> SkyCoord:
    return SkyCoord(ra, dec, unit=(u.hourangle, u.deg))


def _sky_error_arcsec(position: ephemeris.CometPosition, reference: SkyCoord) -> float:
    ours = SkyCoord(ra=position.ra_deg * u.deg, dec=position.dec_deg * u.deg)
    return float(ours.separation(reference).arcsec)


@pytest.mark.parametrize(
    ("orbit", "ra", "dec", "r_au", "delta_au"),
    [
        # JPL Horizons, 2026-Oct-04 00:00 UT
        (TEMPEL_2, "22 50 24.70", "-33 10 44.1", 1.561866809378, 0.68620693113473),
        (PANSTARRS_R3, "07 30 49.28", "-26 25 51.2", 2.921467288409, 2.98985983188912),
    ],
)
def test_comet_position_matches_jpl_horizons(orbit, ra, dec, r_au, delta_au) -> None:
    position = ephemeris.comet_position(orbit, BAD_HOMBURG, WHEN)
    assert _sky_error_arcsec(position, _hms_dms(ra, dec)) < 30.0
    assert position.earth_distance_au == pytest.approx(delta_au, abs=1e-3)
    assert position.sun_distance_au == pytest.approx(r_au, abs=1e-3)


def test_parabolic_orbit_is_continuous_with_a_near_parabolic_one() -> None:
    """e == 1 takes its own branch (semilatus rectum 2q); it must agree
    with an orbit a hair short of parabolic."""
    parabolic = replace(PANSTARRS_R3, eccentricity=1.0)
    almost = replace(PANSTARRS_R3, eccentricity=1.0 - 1e-9)
    a = ephemeris.comet_position(parabolic, BAD_HOMBURG, WHEN)
    b = ephemeris.comet_position(almost, BAD_HOMBURG, WHEN)
    reference = SkyCoord(ra=b.ra_deg * u.deg, dec=b.dec_deg * u.deg)
    assert _sky_error_arcsec(a, reference) < 0.1


def test_comet_target_freezes_the_position_at_the_given_moment() -> None:
    target = comets.comet_target(TEMPEL_2, BAD_HOMBURG, WHEN)
    position = ephemeris.comet_position(TEMPEL_2, BAD_HOMBURG, WHEN)

    assert (target.ra_deg, target.dec_deg) == (position.ra_deg, position.dec_deg)
    assert target.name == target.catalog_id == "10P/Tempel"
    assert target.types == ("comet",)
    assert target.size_arcmin == (0.0, 0.0)  # coma/tail not modeled
    assert target.magnitude is None  # an observation, not geometry


def test_sky_motion_matches_the_mpc_ephemeris() -> None:
    """MPC Ephemeris Service: 0.69"/min for 10P at this moment."""
    motion = comets.sky_motion_deg_per_hour(TEMPEL_2, BAD_HOMBURG, WHEN)
    assert motion * 3600.0 / 60.0 == pytest.approx(0.69, abs=0.05)

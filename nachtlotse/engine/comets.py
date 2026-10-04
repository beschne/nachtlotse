"""Comets as rankable targets — pure, deterministic, offline.

A comet moves against the stars, but slowly enough (typically well under a
degree per night) that ranking it like any catalog object works: freeze its
position at one representative moment — the middle of the night's dark
window — and hand that to the same engine (`constraints.best_time_tonight`,
`framing`, `framing_preview`) every other `Target` goes through. Its
actual motion is reported alongside (`sky_motion_deg_per_hour`), so a fast
mover never hides behind the snapshot.

Positions come from `ephemeris.comet_position` (two-body propagation of
MPC elements). Brightness deliberately doesn't: see `CometOrbit`'s
docstring — it comes from observations, outside the engine.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from astropy import units as u
from astropy.coordinates import SkyCoord

from nachtlotse.engine import ephemeris
from nachtlotse.engine.models import CometOrbit, Site, Target


def comet_target(orbit: CometOrbit, site: Site, when: datetime) -> Target:
    """`orbit`'s comet as a fixed `Target` at its position at `when`.
    Size unknown (coma and tail aren't modeled), so framing treats it as
    unconstrained, and no magnitude — that's an observation, not geometry.
    No `catalog_id` either: the designation is its name, and every label
    built from "catalog_id name" would otherwise print it twice."""
    position = ephemeris.comet_position(orbit, site, when)
    return Target(
        name=orbit.designation,
        ra_deg=position.ra_deg,
        dec_deg=position.dec_deg,
        types=("comet",),
    )


def sky_motion_deg_per_hour(orbit: CometOrbit, site: Site, when: datetime) -> float:
    """How fast the comet moves against the stars at `when`, over a
    symmetric one-hour baseline."""
    half = timedelta(minutes=30)
    before = ephemeris.comet_position(orbit, site, when - half)
    after = ephemeris.comet_position(orbit, site, when + half)
    start = SkyCoord(ra=before.ra_deg * u.deg, dec=before.dec_deg * u.deg)
    end = SkyCoord(ra=after.ra_deg * u.deg, dec=after.dec_deg * u.deg)
    return float(start.separation(end).deg)

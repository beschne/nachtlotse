"""Messier core catalog (~30 objects) — data, not engine logic.

Coordinates are J2000 equinox, accurate to roughly an arcminute — good enough
for altitude ranking, not for plate-solving/pointing. `size_arcmin` is the
published apparent (major, minor) axis — approximate values from standard
Messier references, good for framing heuristics, not precision use.
"""

from __future__ import annotations

from nachtlotse.engine.models import Target

MESSIER_CORE: list[Target] = [
    Target(
        name="Crab Nebula",
        ra_deg=83.633,
        dec_deg=22.017,
        catalog_id="M1",
        size_arcmin=(6.0, 4.0),
    ),
    Target(
        name="Lagoon Nebula",
        ra_deg=270.950,
        dec_deg=-24.383,
        catalog_id="M8",
        size_arcmin=(90.0, 40.0),
    ),
    Target(
        name="Wild Duck Cluster",
        ra_deg=282.775,
        dec_deg=-6.267,
        catalog_id="M11",
        size_arcmin=(14.0, 14.0),
    ),
    Target(
        name="Hercules Cluster",
        ra_deg=250.425,
        dec_deg=36.467,
        catalog_id="M13",
        size_arcmin=(20.0, 20.0),
    ),
    Target(
        name="Pegasus Cluster",
        ra_deg=322.500,
        dec_deg=12.167,
        catalog_id="M15",
        size_arcmin=(18.0, 18.0),
    ),
    Target(
        name="Eagle Nebula",
        ra_deg=274.700,
        dec_deg=-13.783,
        catalog_id="M16",
        size_arcmin=(35.0, 28.0),
    ),
    Target(
        name="Omega Nebula",
        ra_deg=275.200,
        dec_deg=-16.183,
        catalog_id="M17",
        size_arcmin=(20.0, 15.0),
    ),
    Target(
        name="Trifid Nebula",
        ra_deg=270.575,
        dec_deg=-23.033,
        catalog_id="M20",
        size_arcmin=(28.0, 28.0),
    ),
    Target(
        name="Sagittarius Cluster",
        ra_deg=279.100,
        dec_deg=-23.900,
        catalog_id="M22",
        size_arcmin=(24.0, 24.0),
    ),
    Target(
        name="Dumbbell Nebula",
        ra_deg=299.900,
        dec_deg=22.717,
        catalog_id="M27",
        size_arcmin=(8.0, 5.6),
    ),
    Target(
        name="Andromeda Galaxy",
        ra_deg=10.6847,
        dec_deg=41.2692,
        catalog_id="M31",
        size_arcmin=(190.0, 60.0),
    ),
    Target(
        name="Triangulum Galaxy",
        ra_deg=23.475,
        dec_deg=30.650,
        catalog_id="M33",
        size_arcmin=(61.0, 42.0),
    ),
    Target(
        name="Shoe-Buckle Cluster",
        ra_deg=92.250,
        dec_deg=24.350,
        catalog_id="M35",
        size_arcmin=(28.0, 28.0),
    ),
    Target(
        name="Pinwheel Cluster",
        ra_deg=84.025,
        dec_deg=34.133,
        catalog_id="M36",
        size_arcmin=(12.0, 12.0),
    ),
    Target(
        name="Salt-and-Pepper Cluster",
        ra_deg=88.100,
        dec_deg=32.550,
        catalog_id="M37",
        size_arcmin=(24.0, 24.0),
    ),
    Target(
        name="Orion Nebula",
        ra_deg=83.850,
        dec_deg=-5.450,
        catalog_id="M42",
        size_arcmin=(85.0, 60.0),
    ),
    Target(
        name="Beehive Cluster",
        ra_deg=130.100,
        dec_deg=19.983,
        catalog_id="M44",
        size_arcmin=(95.0, 95.0),
    ),
    Target(
        name="Pleiades",
        ra_deg=56.750,
        dec_deg=24.117,
        catalog_id="M45",
        size_arcmin=(110.0, 110.0),
    ),
    Target(
        name="Whirlpool Galaxy",
        ra_deg=202.475,
        dec_deg=47.200,
        catalog_id="M51",
        size_arcmin=(11.0, 7.0),
    ),
    Target(
        name="Ring Nebula",
        ra_deg=283.400,
        dec_deg=33.033,
        catalog_id="M57",
        size_arcmin=(1.4, 1.0),
    ),
    Target(
        name="Sunflower Galaxy",
        ra_deg=198.950,
        dec_deg=42.033,
        catalog_id="M63",
        size_arcmin=(10.0, 6.0),
    ),
    Target(
        name="Black Eye Galaxy",
        ra_deg=194.175,
        dec_deg=21.683,
        catalog_id="M64",
        size_arcmin=(9.3, 5.4),
    ),
    Target(
        name="Leo Triplet — M65",
        ra_deg=169.725,
        dec_deg=13.083,
        catalog_id="M65",
        size_arcmin=(9.8, 2.9),
    ),
    Target(
        name="Leo Triplet — M66",
        ra_deg=170.050,
        dec_deg=12.983,
        catalog_id="M66",
        size_arcmin=(9.1, 4.2),
    ),
    Target(
        name="Phantom Galaxy",
        ra_deg=24.175,
        dec_deg=15.783,
        catalog_id="M74",
        size_arcmin=(10.5, 9.5),
    ),
    Target(
        name="Bode's Galaxy",
        ra_deg=148.900,
        dec_deg=69.067,
        catalog_id="M81",
        size_arcmin=(27.0, 14.0),
    ),
    Target(
        name="Cigar Galaxy",
        ra_deg=148.950,
        dec_deg=69.683,
        catalog_id="M82",
        size_arcmin=(11.0, 5.0),
    ),
    Target(
        name="Southern Pinwheel Galaxy",
        ra_deg=204.250,
        dec_deg=-29.867,
        catalog_id="M83",
        size_arcmin=(13.0, 12.0),
    ),
    Target(
        name="Pinwheel Galaxy",
        ra_deg=210.800,
        dec_deg=54.350,
        catalog_id="M101",
        size_arcmin=(29.0, 27.0),
    ),
    Target(
        name="Sombrero Galaxy",
        ra_deg=190.000,
        dec_deg=-11.617,
        catalog_id="M104",
        size_arcmin=(9.0, 4.0),
    ),
]

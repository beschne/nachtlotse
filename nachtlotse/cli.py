"""Command-line interface — the outermost UI boundary.

Imports the engine and data layers; local-timezone conversion for display
happens only here, never inside the engine core (UTC internally throughout).
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from astroplan import moon_illumination
from astropy.time import Time

from nachtlotse.data.catalog import MESSIER_CORE
from nachtlotse.engine import constraints, ephemeris
from nachtlotse.engine.models import (
    HorizonProfile,
    Mount,
    Optics,
    Rig,
    Sensor,
    Site,
    Target,
)

BAD_HOMBURG = Site(
    name="Bad Homburg",
    lat_deg=50.2266,
    lon_deg=8.6180,
    elevation_m=190.0,
    tz="Europe/Berlin",
    horizon=HorizonProfile(points=[]),
)

SEESTAR_S30_PRO = Rig(
    name="ZWO Seestar S30 Pro",
    optics=Optics(
        name="Seestar S30 Pro Optics", focal_length_mm=160.0, aperture_mm=30.0
    ),
    sensor=Sensor(name="Sony IMX585", width_px=3840, height_px=2160, pixel_um=2.9),
    mount=Mount(name="Seestar S30 Pro Mount", kind="altaz"),
)


def _rank_targets(
    site: Site, when: datetime
) -> list[tuple[Target, datetime, ephemeris.AltAz]]:
    """Rank catalog targets by max altitude within tonight's dark window.

    A target is dropped if it never simultaneously clears the altitude,
    astronomical-night, and moon-separation constraints during that window
    (see `engine.constraints`). Horizon-profile and framing constraints land
    in M2/M3.
    """
    evening_start, morning_end = constraints.dark_window(site, when)

    ranked: list[tuple[Target, datetime, ephemeris.AltAz]] = []
    for target in MESSIER_CORE:
        if not constraints.is_observable_tonight(site, target, when):
            continue
        max_time, pos = ephemeris.max_altitude(site, target, evening_start, morning_end)
        ranked.append((target, max_time, pos))
    ranked.sort(key=lambda row: row[2].alt_deg, reverse=True)
    return ranked


def _cmd_today() -> int:
    site = BAD_HOMBURG
    rig = SEESTAR_S30_PRO
    now = datetime.now(UTC)
    local_tz = ZoneInfo(site.tz)

    evening_start, morning_end = constraints.dark_window(site, now)
    illumination_pct = moon_illumination(Time(now)) * 100

    print(f"Nachtlotse — {site.name} ({rig.name})")
    print(
        f"Dark window: {evening_start.astimezone(local_tz):%Y-%m-%d %H:%M} – "
        f"{morning_end.astimezone(local_tz):%H:%M %Z}  ·  Moon: {illumination_pct:.0f}% illuminated"
    )
    print()

    ranked = _rank_targets(site, now)
    if not ranked:
        print("No catalog target clears altitude/moon/night constraints tonight.")
        return 0

    print(f"{'Target':<32} {'Max Alt':>8} {'Az':>7}  Best time (local)")
    for target, max_time, pos in ranked:
        label = f"{target.catalog_id} {target.name}"
        local_time = max_time.astimezone(local_tz)
        print(
            f"{label:<32} {pos.alt_deg:7.1f}° {pos.az_deg:6.1f}°  "
            f"{local_time:%Y-%m-%d %H:%M %Z}"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lotse",
        description="Nachtlotse — deterministic astrophotography session planner",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "today", help="Rank tonight's observable Messier-core targets by max altitude"
    )
    args = parser.parse_args(argv)

    if args.command == "today":
        return _cmd_today()
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

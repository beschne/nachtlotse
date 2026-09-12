"""Command-line interface — the outermost UI boundary.

Imports the engine and data layers; local-timezone conversion for display
happens only here, never inside the engine core (UTC internally throughout).
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from nachtlotse.data.catalog import MESSIER_CORE
from nachtlotse.engine import ephemeris
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

_RANKING_WINDOW_HOURS = 24


def _rank_targets(
    site: Site, when: datetime
) -> list[tuple[Target, datetime, ephemeris.AltAz]]:
    """Rank catalog targets by max altitude (transit) within the next 24h.

    No twilight/moon/horizon constraints yet — those land in M1/M2. A target
    is dropped only if it never rises above the local horizon (alt <= 0) at
    this site.
    """
    window_end = when + timedelta(hours=_RANKING_WINDOW_HOURS)
    ranked: list[tuple[Target, datetime, ephemeris.AltAz]] = []
    for target in MESSIER_CORE:
        try:
            transit_time = ephemeris.find_transit(site, target, when, window_end)
        except ValueError:
            continue
        pos = ephemeris.altaz(site, target, transit_time)
        if pos.alt_deg <= 0.0:
            continue
        ranked.append((target, transit_time, pos))
    ranked.sort(key=lambda row: row[2].alt_deg, reverse=True)
    return ranked


def _cmd_today() -> int:
    site = BAD_HOMBURG
    rig = SEESTAR_S30_PRO
    now = datetime.now(UTC)
    local_tz = ZoneInfo(site.tz)

    ranked = _rank_targets(site, now)

    print(f"Nachtlotse — {site.name} ({rig.name})")
    print(f"{'Target':<32} {'Max Alt':>8} {'Az @ Transit':>13}  Transit (local)")
    for target, transit_time, pos in ranked:
        label = f"{target.catalog_id} {target.name}"
        local_time = transit_time.astimezone(local_tz)
        print(
            f"{label:<32} {pos.alt_deg:7.1f}° {pos.az_deg:12.1f}°  "
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
        "today", help="Rank tonight's Messier-core targets by max altitude"
    )
    args = parser.parse_args(argv)

    if args.command == "today":
        return _cmd_today()
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

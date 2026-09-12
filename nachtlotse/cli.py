"""Command-line interface — the outermost UI boundary.

Imports the engine and data layers; local-timezone conversion for display
happens only here, never inside the engine core (UTC internally throughout).
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from astroplan import moon_illumination
from astropy.time import Time

from nachtlotse.data import store
from nachtlotse.data.catalog import MESSIER_CORE
from nachtlotse.data.store import SiteRecord
from nachtlotse.engine import constraints, ephemeris
from nachtlotse.engine.models import Mount, Optics, Rig, Sensor, Site, Target

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
    """Rank catalog targets by their best moment within tonight's dark window.

    A target is dropped unless some moment tonight simultaneously clears
    altitude, astronomical night, moon separation, and the site's horizon
    profile (see `engine.constraints.best_time_tonight`). Framing/field-
    rotation constraints land in M3.
    """
    ranked: list[tuple[Target, datetime, ephemeris.AltAz]] = []
    for target in MESSIER_CORE:
        result = constraints.best_time_tonight(site, target, when)
        if result is None:
            continue
        best_time, pos = result
        ranked.append((target, best_time, pos))
    ranked.sort(key=lambda row: row[2].alt_deg, reverse=True)
    return ranked


def _cmd_today(site_name: str | None) -> int:
    try:
        record = (
            store.get_site_record(site_name)
            if site_name
            else store.default_site_record()
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    site = record.site
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
        print(
            "No catalog target clears altitude/moon/night/horizon constraints tonight."
        )
        return 0

    print(f"{'Target':<32} {'Max Alt':>8} {'Az':>7}  Best time (local)")
    for target, best_time, pos in ranked:
        label = f"{target.catalog_id} {target.name}"
        local_time = best_time.astimezone(local_tz)
        print(
            f"{label:<32} {pos.alt_deg:7.1f}° {pos.az_deg:6.1f}°  "
            f"{local_time:%Y-%m-%d %H:%M %Z}"
        )
    return 0


def _format_site_line(record: SiteRecord) -> str:
    site = record.site
    profile = "measured" if len(site.horizon.points) > 4 else "flat/sector"
    aliases = f" (aka {', '.join(record.aliases)})" if record.aliases else ""
    details = (
        f"    {site.lat_deg:.5f}°N {site.lon_deg:.5f}°E, {site.elevation_m:.0f} m · "
        f"{record.region} · Bortle {record.bortle} · horizon: {profile}"
    )
    lines = [f"{site.name}{aliases}", details]
    if record.address:
        lines.append(f"    {record.address}")
    return "\n".join(lines)


def _cmd_sites() -> int:
    try:
        store.require_sites()
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    print("Nachtlotse — known sites")
    print()
    for record in store.SITES:
        print(_format_site_line(record))
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lotse",
        description="Nachtlotse — deterministic astrophotography session planner",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    today_parser = subparsers.add_parser(
        "today", help="Rank tonight's observable Messier-core targets by max altitude"
    )
    today_parser.add_argument(
        "--site",
        default=None,
        help="Site name or alias (default: the first site in your local site list)",
    )

    subparsers.add_parser("sites", help="List all known observing sites")

    args = parser.parse_args(argv)

    if args.command == "today":
        return _cmd_today(args.site)
    if args.command == "sites":
        return _cmd_sites()
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

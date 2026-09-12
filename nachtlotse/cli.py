"""Command-line interface — the outermost UI boundary.

Imports the engine and data layers; local-timezone conversion for display
happens only here, never inside the engine core (UTC internally throughout).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from astroplan import moon_illumination
from astropy.time import Time

from nachtlotse.data import store
from nachtlotse.data.catalog import MESSIER_CORE
from nachtlotse.data.store import RigRecord, SiteRecord
from nachtlotse.engine import constraints, ephemeris, framing
from nachtlotse.engine.models import Rig, Site, Target


def _rotation_gate(
    rig: Rig, site: Site, target: Target
) -> Callable[[datetime, ephemeris.AltAz], bool] | None:
    """An `extra_ok` callback for `best_time_tonight`, or None for eq rigs
    (which have no field-rotation problem to gate on)."""
    if rig.mount.kind != "altaz":
        return None

    def gate(sample_time: datetime, _pos: ephemeris.AltAz) -> bool:
        return framing.has_safe_field_rotation(rig, site, target, sample_time)

    return gate


def _rank_targets(
    site: Site, rig: Rig, when: datetime
) -> list[tuple[Target, datetime, ephemeris.AltAz, float]]:
    """Rank catalog targets by their best moment within tonight's dark window.

    A target is dropped unless some moment tonight simultaneously clears
    altitude, astronomical night, moon separation, the site's horizon
    profile, and — for alt-az rigs only — safe field rotation near the
    zenith (see `engine.constraints.best_time_tonight` / `engine.framing`).
    Each row also carries a framing score (0..1): how well the target's
    angular size fits `rig`'s field of view.
    """
    ranked: list[tuple[Target, datetime, ephemeris.AltAz, float]] = []
    for target in MESSIER_CORE:
        result = constraints.best_time_tonight(
            site, target, when, extra_ok=_rotation_gate(rig, site, target)
        )
        if result is None:
            continue
        best_time, pos = result
        ranked.append((target, best_time, pos, framing.framing_score(rig, target)))
    ranked.sort(key=lambda row: row[2].alt_deg, reverse=True)
    return ranked


def _cmd_today(site_name: str | None, rig_name: str | None) -> int:
    try:
        site_record = (
            store.get_site_record(site_name)
            if site_name
            else store.default_site_record()
        )
        rig_record = (
            store.get_rig_record(rig_name) if rig_name else store.default_rig_record()
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    site = site_record.site
    rig = rig_record.rig
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

    ranked = _rank_targets(site, rig, now)
    if not ranked:
        print(
            "No catalog target clears altitude/moon/night/horizon/rotation "
            "constraints tonight."
        )
        return 0

    print(f"{'Target':<32} {'Max Alt':>8} {'Az':>7} {'Fit':>5}  Best time (local)")
    for target, best_time, pos, fit in ranked:
        label = f"{target.catalog_id} {target.name}"
        local_time = best_time.astimezone(local_tz)
        print(
            f"{label:<32} {pos.alt_deg:7.1f}° {pos.az_deg:6.1f}° {fit:5.2f}  "
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


def _format_rig_line(record: RigRecord) -> str:
    rig = record.rig
    aliases = f" (aka {', '.join(record.aliases)})" if record.aliases else ""
    fov_width_deg, fov_height_deg = rig.fov_deg
    return (
        f"{rig.name}{aliases}\n"
        f"    {rig.optics.focal_length_mm:.0f} mm f/"
        f"{rig.optics.focal_length_mm / rig.optics.aperture_mm:.1f} "
        f"({rig.optics.aperture_mm:.0f} mm aperture) · "
        f"{rig.sensor.width_px}×{rig.sensor.height_px} px, "
        f"{rig.sensor.pixel_um:.2f} µm · mount: {rig.mount.kind}\n"
        f"    FoV {fov_width_deg:.2f}° × {fov_height_deg:.2f}° · "
        f"sampling {rig.sampling_arcsec_px:.2f}″/px"
    )


def _cmd_rigs() -> int:
    try:
        store.require_rigs()
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    print("Nachtlotse — known rigs")
    print()
    for record in store.RIGS:
        print(_format_rig_line(record))
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
    today_parser.add_argument(
        "--rig",
        default=None,
        help="Rig name or alias (default: the first rig in your local rig list)",
    )

    subparsers.add_parser("sites", help="List all known observing sites")
    subparsers.add_parser("rigs", help="List all known rigs")

    args = parser.parse_args(argv)

    if args.command == "today":
        return _cmd_today(args.site, args.rig)
    if args.command == "sites":
        return _cmd_sites()
    if args.command == "rigs":
        return _cmd_rigs()
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

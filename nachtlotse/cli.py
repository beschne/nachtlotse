"""Command-line interface — the outermost UI boundary.

Imports the engine and data layers (via `planning`); local-timezone
conversion for display happens only here, never inside the engine core
(UTC internally throughout).
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from typing import get_args
from zoneinfo import ZoneInfo

from nachtlotse import planning
from nachtlotse.data import store
from nachtlotse.data.store import RigRecord, SiteRecord
from nachtlotse.engine import framing
from nachtlotse.engine.models import TARGET_TYPE_LABELS, TargetType, WeatherSummary

_TARGET_TYPE_CHOICES = sorted(get_args(TargetType))


def _format_types(types: tuple[str, ...]) -> str:
    return "/".join(TARGET_TYPE_LABELS.get(t, t) for t in types)


def _format_weather_line(weather: WeatherSummary | None) -> str:
    if weather is None:
        return "Weather: unavailable (offline or Open-Meteo unreachable)"
    return (
        f"Weather: clouds up to {weather.max_cloud_cover_pct:.0f}% "
        f"(avg {weather.avg_cloud_cover_pct:.0f}%) · "
        f"wind up to {weather.max_wind_kmh:.0f} km/h · "
        f"dew margin {weather.min_dew_point_spread_c:.1f}°C"
    )


def _cmd_plan(
    site_name: str | None,
    rig_name: str | None,
    date_str: str | None,
    types: list[str] | None,
) -> int:
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
    local_tz = ZoneInfo(site.tz)

    if date_str is None:
        now = datetime.now(UTC)
    else:
        try:
            target_date = date.fromisoformat(date_str)
        except ValueError:
            print(f"Invalid --date {date_str!r}, expected YYYY-MM-DD", file=sys.stderr)
            return 2
        # Noon local time on that date: unambiguously daytime, so
        # dark_window picks the night starting that evening.
        now = datetime(
            target_date.year, target_date.month, target_date.day, 12, 0, tzinfo=local_tz
        )

    type_filter = frozenset(types) if types else None
    plan = planning.plan_night(site, rig, now, types=type_filter)

    print(f"Nachtlotse — {site.name} ({rig.name})")
    print(
        f"Dark window: {plan.evening_start.astimezone(local_tz):%Y-%m-%d %H:%M} – "
        f"{plan.morning_end.astimezone(local_tz):%H:%M %Z}  ·  "
        f"Moon: {plan.moon_illumination_pct:.0f}% illuminated"
    )
    print(_format_weather_line(plan.weather))
    print()

    if not plan.ranked:
        suffix = " matching --type" if type_filter else ""
        print(
            f"No catalog target{suffix} clears altitude/moon/night/horizon/"
            "rotation constraints tonight."
        )
        return 0

    print("Shortlist:")
    for rank, (row, verdict) in enumerate(plan.shortlist, start=1):
        label = f"{row.target.catalog_id} {row.target.name}".strip()
        print(f"  {rank}. Verdict: {verdict.level} — {label}")
        for reason in verdict.reasons:
            print(f"       {reason}")
    print()

    print(
        f"{'Target':<32} {'Type':<32} {'Max Alt':>8} {'Az':>7} {'Fit':>5}  "
        "Best time (local)"
    )
    for target, best_time, pos, fit in plan.ranked:
        label = f"{target.catalog_id} {target.name}"
        local_time = best_time.astimezone(local_tz)
        print(
            f"{label:<32} {_format_types(target.types):<32} {pos.alt_deg:7.1f}° "
            f"{pos.az_deg:6.1f}° {fit:5.2f}  {local_time:%Y-%m-%d %H:%M %Z}"
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


_RIG_LIST_REFERENCE_BORTLE_CLASSES = (2.0, 5.0)


def _format_rig_line(record: RigRecord) -> str:
    rig = record.rig
    aliases = f" (aka {', '.join(record.aliases)})" if record.aliases else ""
    fov_width_deg, fov_height_deg = rig.fov_deg
    limiting_mags = ", ".join(
        f"Bortle {bortle_class:.0f} ~{framing.photographic_limiting_magnitude(rig.optics.aperture_mm, bortle_class):.1f} mag"
        for bortle_class in _RIG_LIST_REFERENCE_BORTLE_CLASSES
    )
    return (
        f"{rig.name}{aliases}\n"
        f"    {rig.optics.focal_length_mm:.0f} mm f/"
        f"{rig.optics.focal_length_mm / rig.optics.aperture_mm:.1f} "
        f"({rig.optics.aperture_mm:.0f} mm aperture) · "
        f"{rig.sensor.width_px}×{rig.sensor.height_px} px, "
        f"{rig.sensor.pixel_um:.2f} µm · mount: {rig.mount.kind}\n"
        f"    FoV {fov_width_deg:.2f}° × {fov_height_deg:.2f}° · "
        f"sampling {rig.sampling_arcsec_px:.2f}″/px\n"
        f"    Rough limiting magnitude (stacked, tunable estimate): {limiting_mags}"
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

    plan_parser = subparsers.add_parser(
        "plan",
        help="Rank observable Messier-core targets for a night (default: tonight)",
    )
    plan_parser.add_argument(
        "--site",
        default=None,
        help="Site name or alias (default: the first site in your local site list)",
    )
    plan_parser.add_argument(
        "--rig",
        default=None,
        help="Rig name or alias (default: the first rig in your local rig list)",
    )
    plan_parser.add_argument(
        "--date",
        default=None,
        help=(
            "Date to plan for, YYYY-MM-DD, local to the site (default: "
            "tonight). Weather beyond Open-Meteo's forecast horizon shows "
            "as unavailable; the sky-geometry ranking still works for any date."
        ),
    )
    plan_parser.add_argument(
        "--type",
        dest="types",
        action="append",
        choices=_TARGET_TYPE_CHOICES,
        default=None,
        help=(
            "Keep only targets of this category (repeatable — matches any "
            "one of them). Default: no filter."
        ),
    )

    subparsers.add_parser("sites", help="List all known observing sites")
    subparsers.add_parser("rigs", help="List all known rigs")

    args = parser.parse_args(argv)

    if args.command == "plan":
        return _cmd_plan(args.site, args.rig, args.date, args.types)
    if args.command == "sites":
        return _cmd_sites()
    if args.command == "rigs":
        return _cmd_rigs()
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

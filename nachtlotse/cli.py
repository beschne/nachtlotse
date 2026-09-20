"""Command-line interface — the outermost UI boundary.

Imports the engine and data layers (via `planning`); local-timezone
conversion for display happens only here, never inside the engine core
(UTC internally throughout).
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import get_args
from zoneinfo import ZoneInfo

from nachtlotse import best_sky, chart_export, planning
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


class _InvalidDate(Exception):
    """`--date` wasn't a valid YYYY-MM-DD string."""


def _resolve_when(date_str: str | None, local_tz: ZoneInfo) -> datetime:
    """UTC-aware moment to plan for: now, or noon local time on `date_str`
    — unambiguously daytime, so `dark_window` picks the night starting
    that evening. Raises `_InvalidDate` if `date_str` doesn't parse.
    """
    if date_str is None:
        return datetime.now(UTC)
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError:
        raise _InvalidDate(date_str) from None
    return datetime(
        target_date.year, target_date.month, target_date.day, 12, 0, tzinfo=local_tz
    )


def _cmd_plan(
    site_name: str | None,
    rig_name: str | None,
    date_str: str | None,
    types: list[str] | None,
    chart_path: str | None,
    limit: int | None,
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

    try:
        now = _resolve_when(date_str, local_tz)
    except _InvalidDate:
        print(f"Invalid --date {date_str!r}, expected YYYY-MM-DD", file=sys.stderr)
        return 2

    type_filter = frozenset(types) if types else None
    plan = planning.plan_night(site, rig, now, types=type_filter, limit=limit)

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
        f"{'Target':<32} {'Type':<32} {'Max Alt':>8} {'Az':>7} {'Fit':>5} {'Reach':>6}  "
        "Best time (local)"
    )
    for target, best_time, pos, fit, reach in plan.ranked:
        label = f"{target.catalog_id} {target.name}"
        local_time = best_time.astimezone(local_tz)
        print(
            f"{label:<32} {_format_types(target.types):<32} {pos.alt_deg:7.1f}° "
            f"{pos.az_deg:6.1f}° {fit:5.2f} {reach:6.2f}  {local_time:%Y-%m-%d %H:%M %Z}"
        )

    if chart_path is not None:
        try:
            chart_export.save_shortlist_chart(plan, Path(chart_path))
        except chart_export.ChartExportUnavailable as exc:
            print(f"\n{exc}", file=sys.stderr)
            return 2
        print(f"\nChart written to {chart_path}")
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


_COMPASS_POINTS = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
)  # fmt: skip


def _compass_direction(bearing_deg: float) -> str:
    index = round(bearing_deg / 22.5) % len(_COMPASS_POINTS)
    return _COMPASS_POINTS[index]


def _format_site_sky_line(rank: int, report: best_sky.SiteSkyReport) -> str:
    site = report.site
    if report.weather is None:
        weather_part = "weather: unavailable"
    else:
        weather_part = (
            f"clouds up to {report.weather.max_cloud_cover_pct:.0f}% "
            f"(avg {report.weather.avg_cloud_cover_pct:.0f}%)"
        )
    if report.bearing_deg is None:
        distance_part = f"{report.distance_km:.0f} km"
    else:
        direction = _compass_direction(report.bearing_deg)
        distance_part = (
            f"{report.distance_km:.0f} km {report.bearing_deg:.0f}° {direction}"
        )
    return f"  {rank}. {site.name} — {distance_part} — {weather_part}"


def _cmd_best_sky(
    site_name: str | None, radius_km: float | None, date_str: str | None
) -> int:
    try:
        reference_record = (
            store.get_site_record(site_name)
            if site_name
            else store.default_site_record()
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    reference = reference_record.site
    local_tz = ZoneInfo(reference.tz)

    try:
        now = _resolve_when(date_str, local_tz)
    except _InvalidDate:
        print(f"Invalid --date {date_str!r}, expected YYYY-MM-DD", file=sys.stderr)
        return 2

    reports = best_sky.compare_sites(
        reference, store.load_sites(), now, max_distance_km=radius_km
    )

    radius_note = f" within {radius_km:.0f} km" if radius_km is not None else ""
    night_of = now.astimezone(local_tz).date()
    print(
        f"Nachtlotse — best sky near {reference.name}{radius_note} "
        f"— night of {night_of:%Y-%m-%d}"
    )
    print()
    if not reports:
        print("No configured site matches.")
        return 0
    for rank, report in enumerate(reports, start=1):
        print(_format_site_sky_line(rank, report))
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
    plan_parser.add_argument(
        "--chart",
        dest="chart_path",
        nargs="?",
        const=chart_export.DEFAULT_CHART_FILENAME,
        default=None,
        metavar="PATH",
        help=(
            "Write the shortlist's alt/az polar chart as a PNG to PATH "
            f"(default: {chart_export.DEFAULT_CHART_FILENAME} in the "
            "current directory), overwriting any existing file at that "
            "path. Needs `uv sync --extra charts`."
        ),
    )
    plan_parser.add_argument(
        "--limit",
        dest="limit",
        default=None,
        metavar="N",
        type=int,
        help=(
            "Limit evaluated catalog objects to the first N matching any "
            "--type filter (default: 50). Use --limit 0 to evaluate every "
            "catalog object."
        ),
    )

    subparsers.add_parser("sites", help="List all known observing sites")
    subparsers.add_parser("rigs", help="List all known rigs")

    best_sky_parser = subparsers.add_parser(
        "best-sky",
        help="Compare configured sites' forecast cloud cover for the clearest night",
    )
    best_sky_parser.add_argument(
        "--site",
        default=None,
        help=(
            "Reference site name or alias (default: the first site in "
            "your local site list)"
        ),
    )
    best_sky_parser.add_argument(
        "--radius-km",
        type=float,
        default=None,
        metavar="KM",
        help=(
            "Only compare sites within this distance of --site (default: "
            "all configured sites)"
        ),
    )
    best_sky_parser.add_argument(
        "--date",
        default=None,
        help=(
            "Date to compare, YYYY-MM-DD, local to --site (default: "
            "tonight). Weather beyond Open-Meteo's forecast horizon shows "
            "as unavailable."
        ),
    )

    args = parser.parse_args(argv)

    if args.command == "plan":
        return _cmd_plan(
            args.site, args.rig, args.date, args.types, args.chart_path, args.limit
        )
    if args.command == "sites":
        return _cmd_sites()
    if args.command == "rigs":
        return _cmd_rigs()
    if args.command == "best-sky":
        return _cmd_best_sky(args.site, args.radius_km, args.date)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

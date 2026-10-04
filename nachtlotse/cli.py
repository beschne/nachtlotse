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

from nachtlotse import (
    best_sky,
    chart_export,
    frame_export,
    planning,
    prose,
    sky_survey,
)
from nachtlotse.data import catalog, store
from nachtlotse.data.store import RigRecord, SiteRecord
from nachtlotse.engine import constraints, framing, framing_preview, grouping
from nachtlotse.engine.models import (
    TARGET_TYPE_LABELS,
    Site,
    Target,
    TargetType,
    WeatherSummary,
)
from nachtlotse.planning import RankedEntry, RankedGroup, RankedTargetForBestRig
from nachtlotse.weather import open_meteo

_TARGET_TYPE_CHOICES = sorted(get_args(TargetType))


def _format_types(types: tuple[str, ...]) -> str:
    return "/".join(TARGET_TYPE_LABELS.get(t, t) for t in types)


def _target_label(target: Target) -> str:
    return f"{target.catalog_id} {target.name}".strip()


def _entry_label(entry: RankedEntry) -> str:
    """Display label for one ranked entry — joined member names for a
    `RankedGroup` (e.g. "M81 + M82"), the target's own name otherwise.
    A "★ " prefix marks a favorite (ROADMAP.md's "Favorites in the
    catalog") — the reason it's still here even outside the normal
    shortlist cutoff (see `planning._fold_favorites_into_shortlist`)."""
    prefix = "★ " if planning.is_favorite(entry) else ""
    if isinstance(entry, RankedGroup):
        return prefix + " + ".join(_target_label(member) for member in entry.targets)
    return prefix + _target_label(entry.target)


def _entry_types(entry: RankedEntry) -> tuple[str, ...]:
    """Category labels for one ranked entry — every distinct category
    across a group's members, in first-seen order; a single target's own
    otherwise."""
    if isinstance(entry, RankedGroup):
        seen: dict[str, None] = {}
        for member in entry.targets:
            for member_type in member.types:
                seen[member_type] = None
        return tuple(seen)
    return entry.target.types


def _format_weather_line(weather: WeatherSummary | None) -> str:
    if weather is None:
        return "Weather: unavailable (offline or Open-Meteo unreachable)"
    return (
        f"Weather: clouds up to {weather.max_cloud_cover_pct:.0f}% "
        f"(avg {weather.avg_cloud_cover_pct:.0f}%) · "
        f"wind up to {weather.max_wind_kmh:.0f} km/h · "
        f"dew margin {weather.min_dew_point_spread_c:.1f}°C"
    )


# 8 block-height levels, no color — this CLI's output stays plain text/
# ANSI-free throughout, so shading (not hue) is what has to carry cloud
# cover across the night (ROADMAP.md's "Hourly cloud cover for the
# astro-night").
_SPARKLINE_LEVELS = "▁▂▃▄▅▆▇█"


def _sparkline(percentages: list[float]) -> str:
    """One `_SPARKLINE_LEVELS` character per value, 0-100 -> the 8
    height levels."""
    chars = []
    for pct in percentages:
        level = int(pct / 100.0 * len(_SPARKLINE_LEVELS))
        level = max(0, min(len(_SPARKLINE_LEVELS) - 1, level))
        chars.append(_SPARKLINE_LEVELS[level])
    return "".join(chars)


def _hourly_cloud_cover_line(
    hourly: list[open_meteo.HourlyWeather], local_tz: ZoneInfo
) -> str | None:
    """A compact sparkline of cloud cover across the dark window, one
    character per forecast hour — real Open-Meteo hours, not resampled
    or interpolated, so a short summer night is a short bar rather than
    a padded one. None when there's no hourly forecast to show (same
    "no data" case `_format_weather_line` already handles for the
    aggregated summary)."""
    if not hourly:
        return None
    bar = _sparkline([hour.cloud_cover_pct for hour in hourly])
    start_local = hourly[0].when.astimezone(local_tz)
    end_local = hourly[-1].when.astimezone(local_tz)
    return (
        f"Clouds tonight: {bar}  ({start_local:%H:%M}–{end_local:%H:%M} {end_local:%Z})"
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


def _print_prose_briefing(
    plan: planning.NightPlan | planning.NightPlanForBestRig,
) -> int | None:
    """Prints `--prose`'s nightly briefing for `plan`, or an actionable
    error to stderr. Returns an exit code the caller should return
    immediately, or None to keep going (the briefing printed fine)."""
    try:
        briefing = prose.generate_nightly_briefing(plan)
    except prose.ProseUnavailable as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2
    print(f"\nNightly briefing ({prose.resolve_model()}):")
    print(briefing)
    return None


def _dark_window_line(
    plan: planning.NightPlan | planning.NightPlanForBestRig, local_tz: ZoneInfo
) -> str:
    nautical_note = (
        " (nautical only — no astronomical darkness tonight)"
        if plan.darkness == "nautical"
        else ""
    )
    return (
        f"Dark window: {plan.evening_start.astimezone(local_tz):%Y-%m-%d %H:%M} – "
        f"{plan.morning_end.astimezone(local_tz):%H:%M %Z}{nautical_note}  ·  "
        f"Moon: {plan.moon_illumination_pct:.0f}% illuminated"
    )


def _event_line(rank: int, event: planning.RankedEvent, local_tz: ZoneInfo) -> str:
    kind = TARGET_TYPE_LABELS[event.kind].lower()
    local_time = event.best_time.astimezone(local_tz)
    motion = (
        f" · moves {event.motion_deg_per_hour * 60.0:.1f}′/h"
        if event.motion_deg_per_hour is not None
        else ""
    )
    return (
        f"  {rank}. Verdict: {event.verdict.level} — {event.target.name} · {kind} · "
        f"{event.target.magnitude:.1f} mag · best {local_time:%H:%M %Z} · "
        f"alt {event.pos.alt_deg:.0f}° az {event.pos.az_deg:.0f}°{motion}"
    )


def _print_events(report: planning.EventsReport | None, local_tz: ZoneInfo) -> None:
    """`lotse plan`'s "Current events" block — the ones worth shooting
    tonight, a count of the rest (`lotse events` lists them), and where
    the data came from."""
    if report is None:
        return
    print()
    print("Current events (comets observed in the last two weeks):")
    if not report.events:
        print("  none worth shooting tonight")
    for rank, event in enumerate(report.events, start=1):
        print(_event_line(rank, event, local_tz))
        print(f"       brightness: {event.magnitude_source}")
        for reason in event.verdict.reasons:
            print(f"       {reason}")
    if report.skipped:
        print(
            f"  ({len(report.skipped)} more not worth shooting tonight — "
            "`lotse events` lists them with reasons)"
        )
    for note in report.notes:
        print(f"  {note}")


def _cmd_plan(
    site_name: str | None,
    rig_name: str | None,
    date_str: str | None,
    types: list[str] | None,
    chart_path: str | None,
    limit: int | None,
    best_rig: bool,
    want_prose: bool,
    want_events: bool = True,
) -> int:
    if best_rig and rig_name:
        print("--best-rig can't be combined with --rig.", file=sys.stderr)
        return 2
    if best_rig and chart_path is not None:
        print("--best-rig can't be combined with --chart yet.", file=sys.stderr)
        return 2

    try:
        site_record = (
            store.get_site_record(site_name)
            if site_name
            else store.default_site_record()
        )
        if not best_rig:
            rig_record = (
                store.get_rig_record(rig_name)
                if rig_name
                else store.default_rig_record()
            )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    site = site_record.site
    local_tz = ZoneInfo(site.tz)

    try:
        now = _resolve_when(date_str, local_tz)
    except _InvalidDate:
        print(f"Invalid --date {date_str!r}, expected YYYY-MM-DD", file=sys.stderr)
        return 2

    type_filter = frozenset(types) if types else None

    if best_rig:
        return _cmd_plan_best_rig(site, now, type_filter, limit, local_tz, want_prose)

    rig = rig_record.rig
    try:
        plan = planning.plan_night(
            site, rig, now, types=type_filter, limit=limit, include_events=want_events
        )
    except constraints.NoDarkWindow as exc:
        print(exc, file=sys.stderr)
        return 2

    print(f"Nachtlotse — {site.name} ({rig.name})")
    print(_dark_window_line(plan, local_tz))
    print(_format_weather_line(plan.weather))
    hourly_line = _hourly_cloud_cover_line(plan.hourly_cloud_cover, local_tz)
    if hourly_line is not None:
        print(hourly_line)
    print()

    if not plan.ranked:
        suffix = " matching --type" if type_filter else ""
        print(
            f"No catalog target{suffix} clears altitude/moon/night/horizon/"
            "rotation constraints tonight."
        )
        _print_events(plan.events, local_tz)
        return 0

    print("Shortlist:")
    for rank, (row, verdict) in enumerate(plan.shortlist, start=1):
        print(f"  {rank}. Verdict: {verdict.level} — {_entry_label(row)}")
        for reason in verdict.reasons:
            print(f"       {reason}")
    print()

    print(
        f"{'Target':<32} {'Type':<32} {'Max Alt':>8} {'Az':>7} {'Fit':>5} {'Reach':>6}  "
        "Best time (local)"
    )
    for entry in plan.ranked:
        label = _entry_label(entry)
        local_time = entry.best_time.astimezone(local_tz)
        print(
            f"{label:<32} {_format_types(_entry_types(entry)):<32} "
            f"{entry.pos.alt_deg:7.1f}° {entry.pos.az_deg:6.1f}° {entry.fit:5.2f} "
            f"{entry.reach:6.2f}  {local_time:%Y-%m-%d %H:%M %Z}"
        )

    _print_events(plan.events, local_tz)

    if chart_path is not None:
        try:
            chart_export.save_shortlist_chart(plan, Path(chart_path))
        except chart_export.ChartExportUnavailable as exc:
            print(f"\n{exc}", file=sys.stderr)
            return 2
        print(f"\nChart written to {chart_path}")

    if want_prose:
        exit_code = _print_prose_briefing(plan)
        if exit_code is not None:
            return exit_code
    return 0


def _best_rig_target_label(row: RankedTargetForBestRig) -> str:
    """`_target_label`, with the same "★ " favorite prefix `_entry_label`
    uses — the best-rig chooser never groups (see
    `planning.rank_targets_for_best_rig`), so there's no `RankedGroup`
    case to handle here."""
    prefix = "★ " if planning.is_favorite(row) else ""
    return prefix + _target_label(row.target)


def _cmd_plan_best_rig(
    site: Site,
    when: datetime,
    type_filter: frozenset[str] | None,
    limit: int | None,
    local_tz: ZoneInfo,
    want_prose: bool,
) -> int:
    """`--best-rig`'s own rendering path: a rig chosen per target (see
    `planning.plan_night_for_best_rig`), so each row gets its own "Rig"
    column instead of one rig name in the header. No grouping and no
    `--chart` support yet — see `planning.rank_targets_for_best_rig`."""
    try:
        store.require_rigs()
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    rigs = store.load_rigs()

    try:
        plan = planning.plan_night_for_best_rig(
            site, rigs, when, types=type_filter, limit=limit
        )
    except constraints.NoDarkWindow as exc:
        print(exc, file=sys.stderr)
        return 2

    print(f"Nachtlotse — {site.name} (best rig per target, {len(rigs)} configured)")
    print(_dark_window_line(plan, local_tz))
    print(_format_weather_line(plan.weather))
    hourly_line = _hourly_cloud_cover_line(plan.hourly_cloud_cover, local_tz)
    if hourly_line is not None:
        print(hourly_line)
    print()

    if not plan.ranked:
        suffix = " matching --type" if type_filter else ""
        print(
            f"No catalog target{suffix} clears altitude/moon/night/horizon/"
            "rotation constraints tonight, for any configured rig."
        )
        return 0

    print("Shortlist:")
    for rank, (row, verdict) in enumerate(plan.shortlist, start=1):
        label = _best_rig_target_label(row)
        print(f"  {rank}. Verdict: {verdict.level} — {label} ({row.rig.name})")
        for reason in verdict.reasons:
            print(f"       {reason}")
    print()

    print(
        f"{'Target':<32} {'Rig':<24} {'Type':<28} {'Max Alt':>8} {'Az':>7} "
        f"{'Fit':>5} {'Reach':>6}  Best time (local)"
    )
    for row in plan.ranked:
        local_time = row.best_time.astimezone(local_tz)
        print(
            f"{_best_rig_target_label(row):<32} {row.rig.name:<24} "
            f"{_format_types(row.target.types):<28} {row.pos.alt_deg:7.1f}° "
            f"{row.pos.az_deg:6.1f}° {row.fit:5.2f} {row.reach:6.2f}  "
            f"{local_time:%Y-%m-%d %H:%M %Z}"
        )

    if want_prose:
        exit_code = _print_prose_briefing(plan)
        if exit_code is not None:
            return exit_code
    return 0


def _cmd_frame(
    queries: list[str],
    site_name: str | None,
    rig_name: str | None,
    date_str: str | None,
    out_path: str | None,
    want_survey: bool,
) -> int:
    """`lotse frame`: one target (or several sharing one frame) drawn in
    the rig's field of view at its best moment tonight — see
    `engine.framing_preview` and `frame_export`."""
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

    # Catalog objects first; anything else may be a current event (a comet
    # observed lately) — looked up only if needed, it costs a fetch.
    events: planning.EventsReport | None = None
    resolved: list[Target] = []
    motions: dict[str, float] = {}
    for query in queries:
        try:
            resolved.append(catalog.find_target(query))
            continue
        except ValueError as exc:
            catalog_error = exc
        if events is None:
            events = planning.current_events(site, rig, now)
        match = planning.find_event(events, query)
        if isinstance(match, planning.RankedEvent):
            resolved.append(match.target)
            if match.motion_deg_per_hour is not None:
                motions[match.target.name] = match.motion_deg_per_hour
        elif isinstance(match, planning.SkippedEvent):
            print(f"{match.name}: {match.reason}.", file=sys.stderr)
            return 2
        else:
            print(f"{catalog_error} Nor is it a current event.", file=sys.stderr)
            return 2
    targets = tuple(dict.fromkeys(resolved))  # same object named twice

    if not grouping.co_visible_group(rig, targets):
        print(
            f"These don't fit one frame of {rig.name}: they span "
            f"{grouping.group_span_arcmin(targets):.0f}′, the frame's short "
            f"side is {framing.fov_short_arcmin(rig):.0f}′.",
            file=sys.stderr,
        )
        return 2

    label = " + ".join(_target_label(t) for t in targets)
    print(f"Nachtlotse — framing {label}")
    print(f"{site.name} · {rig.name}")

    try:
        evening_start, morning_end = constraints.dark_window(site, now)
    except constraints.NoDarkWindow as exc:
        print(exc, file=sys.stderr)
        return 2
    best = planning.best_time_for(site, rig, targets, now)
    if best is None:
        frame_time = evening_start + (morning_end - evening_start) / 2
        print(
            "Not observable tonight (altitude, horizon, moon, or field "
            "rotation) — orientation shown at the middle of the dark window, "
            f"{frame_time.astimezone(local_tz):%Y-%m-%d %H:%M %Z}, for reference only."
        )
    else:
        frame_time, pos = best
        print(
            f"Best time: {frame_time.astimezone(local_tz):%Y-%m-%d %H:%M %Z} · "
            f"altitude {pos.alt_deg:.0f}° · azimuth {pos.az_deg:.0f}°"
        )

    preview = framing_preview.framing_preview(
        site,
        rig,
        targets,
        frame_time,
        neighbors=catalog.CATALOG,
        night=(evening_start, morning_end),
    )
    caption = frame_export.summary_lines(preview, rig, targets, local_tz)
    for name, motion in motions.items():
        caption.append(
            f"{name} moves {motion * 60.0:.1f}′/h against the stars — "
            "drawn at its position in the middle of the night"
        )
    for line in caption:
        print(line)

    image: sky_survey.SurveyImage | None = None
    if want_survey:
        try:
            image = sky_survey.fetch_cutout_cached(
                preview.center_ra_deg,
                preview.center_dec_deg,
                sky_survey.cutout_fov_deg(
                    preview.fov_width_arcmin, preview.fov_height_arcmin
                ),
            )
            print(f"Sky image: {image.credit}")
        except sky_survey.SurveyImageUnavailable:
            print("Sky image: unavailable (offline or hips2fits unreachable)")

    path = Path(out_path or frame_export.default_filename(targets))
    try:
        frame_export.save_framing_preview(
            preview,
            path,
            title=frame_export.preview_title(targets, rig, preview, local_tz),
            caption_lines=caption,
            image=image,
            local_tz=local_tz,
        )
    except frame_export.FrameExportUnavailable as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2
    print(f"\nPreview written to {path}")
    return 0


def _cmd_events(
    site_name: str | None, rig_name: str | None, date_str: str | None
) -> int:
    """`lotse events`: every current event known right now — the ones
    worth shooting tonight first, then the rest with the reason each
    doesn't make it."""
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
        report = planning.current_events(
            site,
            rig,
            now,
            darkness=constraints.darkness(site, now),
            weather=planning.fetch_weather_summary(
                site, *constraints.dark_window(site, now)
            ),
        )
    except _InvalidDate:
        print(f"Invalid --date {date_str!r}, expected YYYY-MM-DD", file=sys.stderr)
        return 2
    except constraints.NoDarkWindow as exc:
        print(exc, file=sys.stderr)
        return 2

    limit = framing.event_limiting_magnitude(rig, site, "comet")
    limit_text = f"comets to {limit:.1f} mag" if limit is not None else "no limit"
    print(f"Nachtlotse — current events · {site.name} ({rig.name})")
    print(f"Brightness limit for this rig here: {limit_text}")
    print()
    print("Worth shooting tonight:")
    if not report.events:
        print("  none")
    for rank, event in enumerate(report.events, start=1):
        print(_event_line(rank, event, local_tz))
        print(f"       brightness: {event.magnitude_source}")
        for reason in event.verdict.reasons:
            print(f"       {reason}")
    if report.skipped:
        print()
        print("Not tonight:")
        width = max(len(skipped.name) for skipped in report.skipped)
        for skipped in report.skipped:
            magnitude = (
                f"{skipped.magnitude:.1f} mag" if skipped.magnitude is not None else "—"
            )
            print(f"  {skipped.name:<{width}} {magnitude:>9}  {skipped.reason}")
    print()
    for note in report.notes:
        print(note)
    return 0


def _cmd_gui() -> int:
    """Launches the native GUI — lazily imports `nachtlotse.gui`, whose
    only real dependency (PySide6) is the `gui` extra, so plain `lotse
    plan` never needs it installed. Same contract as `--chart`'s missing
    `matplotlib` / `--prose`'s missing `anthropic`: an actionable stderr
    message and exit code 2, not a traceback."""
    try:
        from nachtlotse.gui.app import main as gui_main
    except ImportError as exc:
        print(
            "The GUI needs the `PySide6` package, which isn't installed — "
            "run `uv sync --extra gui` and try again.",
            file=sys.stderr,
        )
        print(f"({exc})", file=sys.stderr)
        return 2
    return gui_main()


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


def _format_site_sky_line(rank: int, report: best_sky.SiteSkyReport) -> str:
    site = report.site
    if report.weather_unavailable_reason == "no_dark_window":
        weather_part = "no dark window that night"
    elif report.weather is None:
        weather_part = "weather: unavailable"
    else:
        weather_part = (
            f"clouds up to {report.weather.max_cloud_cover_pct:.0f}% "
            f"(avg {report.weather.avg_cloud_cover_pct:.0f}%)"
        )
    if report.bearing_deg is None:
        distance_part = f"{report.distance_km:.0f} km"
    else:
        direction = best_sky.compass_direction(report.bearing_deg)
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
    plan_parser.add_argument(
        "--no-events",
        dest="events",
        action="store_false",
        help=(
            "Skip the 'Current events' block (comets observed in the last "
            "two weeks — fetched from MPC/COBS, cached; offline it just "
            "says so). Not shown with --best-rig either way."
        ),
    )
    plan_parser.add_argument(
        "--best-rig",
        dest="best_rig",
        action="store_true",
        help=(
            "Best-rig chooser: score every configured rig for each target "
            "and keep only the best-scoring one per target, instead of the "
            "single --rig you'd otherwise pass. Mutually exclusive with "
            "--rig and --chart; does not group co-visible targets (see "
            "ROADMAP.md)."
        ),
    )
    plan_parser.add_argument(
        "--prose",
        dest="prose",
        action="store_true",
        help=(
            "Print an LLM-written nightly briefing phrasing the shortlist "
            "above in prose (Claude API; numbers/verdicts come from the "
            "engine only, never the model). Needs `uv sync --extra prose` "
            "and an ANTHROPIC_API_KEY environment variable; only called "
            "when this flag is passed, and fails loudly (not silently) "
            "if the request can't complete."
        ),
    )

    frame_parser = subparsers.add_parser(
        "frame",
        help="Preview how a target (or a group) frames in the rig's field of view",
    )
    frame_parser.add_argument(
        "targets",
        nargs="+",
        metavar="TARGET",
        help=(
            "Catalog ID, alias, or name (e.g. M31, 'NGC 224'), or a current "
            "comet (e.g. 161P, 'C/2026 A2'). Several targets are framed "
            "together, if they fit one frame."
        ),
    )
    frame_parser.add_argument(
        "--site",
        default=None,
        help="Site name or alias (default: the first site in your local site list)",
    )
    frame_parser.add_argument(
        "--rig",
        default=None,
        help="Rig name or alias (default: the first rig in your local rig list)",
    )
    frame_parser.add_argument(
        "--date",
        default=None,
        help=(
            "Night to frame for, YYYY-MM-DD, local to the site (default: "
            "tonight) — sets the best time, and with it the alt-az frame "
            "orientation."
        ),
    )
    frame_parser.add_argument(
        "--out",
        dest="out_path",
        default=None,
        metavar="PATH",
        help=(
            "Write the PNG to PATH (default: nachtlotse-frame-<target>.png "
            "in the current directory), overwriting any existing file. "
            "Needs `uv sync --extra charts`."
        ),
    )
    frame_parser.add_argument(
        "--no-survey",
        dest="survey",
        action="store_false",
        help=(
            "Don't fetch a DSS2 sky image as the backdrop (default: fetch "
            "one from CDS hips2fits, cached in .cache/sky_survey/; without "
            "network the preview is drawn without it)."
        ),
    )

    events_parser = subparsers.add_parser(
        "events",
        help="List current events (comets) — worth shooting tonight, and why not",
    )
    events_parser.add_argument(
        "--site",
        default=None,
        help="Site name or alias (default: the first site in your local site list)",
    )
    events_parser.add_argument(
        "--rig",
        default=None,
        help="Rig name or alias (default: the first rig in your local rig list)",
    )
    events_parser.add_argument(
        "--date",
        default=None,
        help="Night, YYYY-MM-DD, local to the site (default: tonight)",
    )

    subparsers.add_parser("sites", help="List all known observing sites")
    subparsers.add_parser("rigs", help="List all known rigs")
    subparsers.add_parser(
        "gui", help="Launch the native GUI (needs `uv sync --extra gui`)"
    )

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
            args.site,
            args.rig,
            args.date,
            args.types,
            args.chart_path,
            args.limit,
            args.best_rig,
            args.prose,
            args.events,
        )
    if args.command == "frame":
        return _cmd_frame(
            args.targets, args.site, args.rig, args.date, args.out_path, args.survey
        )
    if args.command == "events":
        return _cmd_events(args.site, args.rig, args.date)
    if args.command == "sites":
        return _cmd_sites()
    if args.command == "rigs":
        return _cmd_rigs()
    if args.command == "best-sky":
        return _cmd_best_sky(args.site, args.radius_km, args.date)
    if args.command == "gui":
        return _cmd_gui()
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

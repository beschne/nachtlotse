"""Pure adapters: `planning.NightPlan`/`NightPlanForBestRig` -> GUI-ready
display data.

No PySide6 import anywhere in this module — it has zero dependency on the
GUI toolkit, so it's unit-testable without the `gui` extra installed, and
stays swappable if the framework ever changes again. Mirrors the shape of
`cli.py`'s own private formatting helpers (`_entry_label`, `_entry_types`,
`_format_weather_line`) and `prose.py`'s `build_briefing_facts` — each UI
boundary keeps its own small adapter rather than sharing one, the same
"three similar lines beats a premature abstraction" call CLAUDE.md's
coding conventions favor elsewhere.

`build_shortlist_rows` adapts `plan.shortlist`, which carries a real,
engine-computed `Verdict` per entry (see `planning.plan_night`).
`build_ranked_rows` adapts the full `plan.ranked` list instead — every
evaluated target, in ranked order, but deliberately with no verdict
field, since only shortlisted entries have one; matches `cli.py`'s own
ranked table.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from nachtlotse.data.store import RigRecord, SiteRecord
from nachtlotse.engine import framing
from nachtlotse.engine.models import TARGET_TYPE_LABELS, Target, WeatherSummary
from nachtlotse.planning import (
    NightPlan,
    NightPlanForBestRig,
    RankedGroup,
    RankedTargetForBestRig,
)

# Same two reference sky-darkness classes `cli.py`'s `_format_rig_line`
# quotes a rough limiting magnitude for.
_RIG_LIST_REFERENCE_BORTLE_CLASSES = (2.0, 5.0)


def target_label(target: Target) -> str:
    return f"{target.catalog_id} {target.name}".strip()


def _entry_targets(ranked: object) -> tuple[Target, ...]:
    if isinstance(ranked, RankedGroup):
        return ranked.targets
    return (ranked.target,)  # type: ignore[attr-defined]


def entry_label(ranked: object) -> str:
    """Joined member names for a `RankedGroup` (e.g. "M81, M82"), the
    target's own name otherwise — comma-separated here, unlike `cli.py`'s
    `_entry_label`, which joins with " + " for its plain-text table. A
    "★ " prefix marks a favorite (ROADMAP.md's "Favorites in the
    catalog"), same convention as `cli.py`'s own `_entry_label`."""
    targets = _entry_targets(ranked)
    prefix = "★ " if any(target.favorite for target in targets) else ""
    return prefix + ", ".join(target_label(target) for target in targets)


def entry_type_label(ranked: object) -> str:
    """Every distinct category across a group's members, in first-seen
    order, "/"-joined — a single target's own otherwise."""
    if isinstance(ranked, RankedGroup):
        seen: dict[str, None] = {}
        for member in ranked.targets:
            for member_type in member.types:
                seen[member_type] = None
        types: tuple[str, ...] = tuple(seen)
    else:
        types = ranked.target.types  # type: ignore[attr-defined]
    return "/".join(TARGET_TYPE_LABELS.get(t, t) for t in types)


def _best_time_text(local_time: datetime) -> str:
    """Time + zone only, no date — the table's own header already shows
    the dark window's date range, and the date is redundant there even
    though a "best time" can fall on the night's second calendar day."""
    return f"{local_time:%H:%M %Z}"


@dataclass(frozen=True)
class ShortlistRow:
    """One shortlisted entry, fully display-ready — a Qt table/list cell
    never needs to dig into `RankedTarget`/`RankedGroup`/
    `RankedTargetForBestRig` itself."""

    label: str
    type_label: str
    alt_text: str
    az_text: str
    fit_text: str
    reach_text: str
    best_time_text: str
    rig_name: str | None  # only set for NightPlanForBestRig entries
    verdict_level: str
    verdict_reasons: tuple[str, ...]


def build_shortlist_rows(
    plan: NightPlan | NightPlanForBestRig, local_tz: ZoneInfo
) -> list[ShortlistRow]:
    rows = []
    for entry in plan.shortlist:
        ranked = entry.ranked
        rig_name = ranked.rig.name if isinstance(ranked, RankedTargetForBestRig) else None
        local_time = ranked.best_time.astimezone(local_tz)
        rows.append(
            ShortlistRow(
                label=entry_label(ranked),
                type_label=entry_type_label(ranked),
                alt_text=f"{ranked.pos.alt_deg:.1f}°",
                az_text=f"{ranked.pos.az_deg:.1f}°",
                fit_text=f"{ranked.fit:.2f}",
                reach_text=f"{ranked.reach:.2f}",
                best_time_text=_best_time_text(local_time),
                rig_name=rig_name,
                verdict_level=entry.verdict.level,
                verdict_reasons=tuple(entry.verdict.reasons),
            )
        )
    return rows


@dataclass(frozen=True)
class RankedRow:
    """One evaluated entry from the full ranked list — no verdict field,
    since only shortlisted entries have a real one (see module docstring)."""

    label: str
    type_label: str
    alt_text: str
    az_text: str
    fit_text: str
    reach_text: str
    best_time_text: str
    rig_name: str | None  # only set for NightPlanForBestRig entries


def build_ranked_rows(
    plan: NightPlan | NightPlanForBestRig, local_tz: ZoneInfo
) -> list[RankedRow]:
    rows = []
    for ranked in plan.ranked:
        rig_name = ranked.rig.name if isinstance(ranked, RankedTargetForBestRig) else None
        local_time = ranked.best_time.astimezone(local_tz)
        rows.append(
            RankedRow(
                label=entry_label(ranked),
                type_label=entry_type_label(ranked),
                alt_text=f"{ranked.pos.alt_deg:.1f}°",
                az_text=f"{ranked.pos.az_deg:.1f}°",
                fit_text=f"{ranked.fit:.2f}",
                reach_text=f"{ranked.reach:.2f}",
                best_time_text=_best_time_text(local_time),
                rig_name=rig_name,
            )
        )
    return rows


def weather_line(weather: WeatherSummary | None) -> str:
    if weather is None:
        return "Weather unavailable (offline or Open-Meteo unreachable)"
    return (
        f"Clouds up to {weather.max_cloud_cover_pct:.0f}% "
        f"(avg {weather.avg_cloud_cover_pct:.0f}%) · "
        f"wind up to {weather.max_wind_kmh:.0f} km/h · "
        f"dew margin {weather.min_dew_point_spread_c:.1f}°C"
    )


@dataclass(frozen=True)
class HeaderSummary:
    dark_window_text: str
    moon_text: str
    weather_text: str
    counts_text: str


def _moon_event_text(
    moonrise: datetime | None, moonset: datetime | None, local_tz: ZoneInfo
) -> str:
    """"rises HH:MM", "sets HH:MM", both, or "" — either can be absent:
    the Moon doesn't necessarily cross the horizon during a given dark
    window (see `planning._moon_rise_set`), and this makes no claim
    about "up"/"down" all night without actually checking, so it just
    omits whichever event didn't happen."""
    parts = []
    if moonrise is not None:
        parts.append(f"rises {moonrise.astimezone(local_tz):%H:%M}")
    if moonset is not None:
        parts.append(f"sets {moonset.astimezone(local_tz):%H:%M}")
    return " · ".join(parts)


def build_header_summary(
    plan: NightPlan | NightPlanForBestRig, local_tz: ZoneInfo
) -> HeaderSummary:
    counts = {"GO": 0, "MARGINAL": 0, "SKIP": 0}
    for entry in plan.shortlist:
        counts[entry.verdict.level] += 1

    moon_text = f"{plan.moon_illumination_pct:.0f}% illuminated"
    event_text = _moon_event_text(plan.moonrise, plan.moonset, local_tz)
    if event_text:
        moon_text = f"{moon_text} · {event_text}"

    return HeaderSummary(
        dark_window_text=(
            f"{plan.evening_start.astimezone(local_tz):%Y-%m-%d %H:%M} – "
            f"{plan.morning_end.astimezone(local_tz):%H:%M %Z}"
        ),
        moon_text=moon_text,
        weather_text=weather_line(plan.weather),
        counts_text=(
            f"{len(plan.shortlist)} shortlisted · {counts['GO']} GO · "
            f"{counts['MARGINAL']} marginal · {counts['SKIP']} skip"
        ),
    )


@dataclass(frozen=True)
class SiteInfo:
    """One configured site, display-ready — mirrors `cli.py`'s own
    `_format_site_line` (`lotse sites`), read-only: this first scaffold
    surfaces what's configured, it doesn't edit `sites_local.yaml`."""

    name: str
    aliases_text: str  # "" if the record has none
    coords_text: str
    region_text: str
    horizon_text: str
    address: str  # "" if the record has none


def build_site_info(record: SiteRecord) -> SiteInfo:
    site = record.site
    profile = "measured" if len(site.horizon.points) > 4 else "flat/sector"
    return SiteInfo(
        name=site.name,
        aliases_text=", ".join(record.aliases),
        coords_text=f"{site.lat_deg:.5f}°N {site.lon_deg:.5f}°E, {site.elevation_m:.0f} m",
        region_text=f"{record.region} · Bortle {record.bortle}",
        horizon_text=f"Horizon: {profile}",
        address=record.address,
    )


@dataclass(frozen=True)
class RigInfo:
    """One configured rig, display-ready — mirrors `cli.py`'s own
    `_format_rig_line` (`lotse rigs`); same read-only scope as
    `SiteInfo`."""

    name: str
    aliases_text: str
    optics_text: str
    sensor_text: str
    fov_text: str
    limiting_mag_text: str


def build_rig_info(record: RigRecord) -> RigInfo:
    rig = record.rig
    fov_width_deg, fov_height_deg = rig.fov_deg
    limiting_mags = ", ".join(
        f"Bortle {bortle_class:.0f} ~"
        f"{framing.photographic_limiting_magnitude(rig.optics.aperture_mm, bortle_class):.1f} mag"
        for bortle_class in _RIG_LIST_REFERENCE_BORTLE_CLASSES
    )
    return RigInfo(
        name=rig.name,
        aliases_text=", ".join(record.aliases),
        optics_text=(
            f"{rig.optics.focal_length_mm:.0f} mm f/"
            f"{rig.optics.focal_length_mm / rig.optics.aperture_mm:.1f} "
            f"({rig.optics.aperture_mm:.0f} mm aperture)"
        ),
        sensor_text=(
            f"{rig.sensor.width_px}×{rig.sensor.height_px} px, "
            f"{rig.sensor.pixel_um:.2f} µm · mount: {rig.mount.kind}"
        ),
        fov_text=f"FoV {fov_width_deg:.2f}° × {fov_height_deg:.2f}° · sampling {rig.sampling_arcsec_px:.2f}″/px",
        limiting_mag_text=f"Rough limiting magnitude (stacked, tunable estimate): {limiting_mags}",
    )

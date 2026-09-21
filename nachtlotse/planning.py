"""Night planning — orchestrates engine, data, and weather into one result.

Sits between the pure `engine` core and any UI. `cli.py` calls
`plan_night()` instead of duplicating this pipeline — a future UI would
do the same, rather than the ranking logic or weather fetch living
twice. This module itself is not UI: no printing, no framework imports
— that's what keeps it shared.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

from astroplan import moon_illumination
from astropy.time import Time

from nachtlotse.data.catalog import CATALOG
from nachtlotse.engine import constraints, ephemeris, framing, grouping, scoring
from nachtlotse.engine.models import (
    Rig,
    Site,
    Target,
    TargetType,
    Verdict,
    WeatherSummary,
)
from nachtlotse.weather import open_meteo


class RankedTarget(NamedTuple):
    """One catalog target's best moment tonight, how well it frames, and
    how reachable its surface brightness is at this site."""

    target: Target
    best_time: datetime
    pos: ephemeris.AltAz
    fit: float
    reach: float


class RankedGroup(NamedTuple):
    """A co-visible group of catalog targets that fit in one frame of the
    rig at a shared moment tonight (see `engine.grouping`) — the
    multi-object counterpart to `RankedTarget`.

    `pos.alt_deg` is the *lowest* member's altitude at the shared
    `best_time` (worst-wins, same convention `reach` and the eventual
    verdict use below) — a group is only as good as its weakest member,
    not its highest. `pos.az_deg` is the group centroid's azimuth, for
    display/chart placement only.
    """

    targets: tuple[Target, ...]
    best_time: datetime
    pos: ephemeris.AltAz
    fit: float
    reach: float


# Either shape a ranked entry can take — see `RankedGroup` above.
RankedEntry = RankedTarget | RankedGroup


class ShortlistEntry(NamedTuple):
    """One shortlisted target (or group) with its own GO/MARGINAL/SKIP
    verdict.

    There is no single hero target and no single verdict for the night —
    each of the top few ranked entries is independently judged on its own
    altitude (see `engine.scoring.verdict_for_target`), so a night can be a
    GO on one target and a SKIP on another.
    """

    ranked: RankedEntry
    verdict: Verdict


# How many of the top-ranked targets get their own verdict. A "handful", per
# the roadmap — not the whole ranking, which can run to dozens of targets.
SHORTLIST_SIZE = 5

# Default maximum number of catalog objects to evaluate per planning run.
# Higher values improve result quality at the cost of planning time.
# Set to 0 (unlimited) or pass limit=0 for full-catalog evaluation.
DEFAULT_MAX_EVALUATED = 50


@dataclass(frozen=True)
class NightPlan:
    """Everything needed to render a plan, independent of any UI."""

    site: Site
    rig: Rig
    evening_start: datetime
    morning_end: datetime
    moon_illumination_pct: float
    # Either can be None: the Moon doesn't necessarily cross the horizon
    # during a given dark window (up all night, or down all night) — see
    # `_moon_rise_set`.
    moonrise: datetime | None
    moonset: datetime | None
    weather: WeatherSummary | None
    ranked: list[RankedEntry]
    # The top SHORTLIST_SIZE of `ranked`, each with its own verdict. Empty
    # only when no catalog target clears constraints tonight at all.
    shortlist: list[ShortlistEntry]


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


def _member_clears_constraints(
    site: Site, rig: Rig, member: Target, sample_time: datetime
) -> bool:
    """Whether one real group member — not the synthetic centroid
    `best_time_tonight` is sampling against — individually clears
    altitude, horizon, moon separation, and (for alt-az rigs) safe field
    rotation at `sample_time`. See `_group_gate`."""
    pos = ephemeris.altaz(site, member, sample_time)
    if pos.alt_deg < constraints.DEFAULT_MIN_ALT_DEG:
        return False
    if not constraints.clears_horizon(site, pos):
        return False
    if (
        constraints.moon_separation_deg(site, member, sample_time)
        < constraints.DEFAULT_MIN_MOON_SEP_DEG
    ):
        return False
    return framing.has_safe_field_rotation(rig, site, member, sample_time)


def _group_gate(
    rig: Rig, site: Site, members: tuple[Target, ...]
) -> Callable[[datetime, ephemeris.AltAz], bool]:
    """An `extra_ok` callback for `best_time_tonight`, checking every
    real group member (not just the synthetic centroid it samples
    against) at each candidate moment — see `_member_clears_constraints`.
    """

    def gate(sample_time: datetime, _centroid_pos: ephemeris.AltAz) -> bool:
        return all(
            _member_clears_constraints(site, rig, member, sample_time)
            for member in members
        )

    return gate


def _group_best_time(
    site: Site, rig: Rig, members: tuple[Target, ...], when: datetime
) -> tuple[datetime, ephemeris.AltAz] | None:
    """The best shared moment tonight at which every member of `members`
    simultaneously clears constraints, or None if there isn't one —
    individually observable members don't guarantee a shared moment
    (e.g. one horizon-blocked exactly while the other peaks).

    Samples around a synthetic centroid target (`grouping.centroid_target`)
    reusing `constraints.best_time_tonight`'s own night-scanning loop,
    the same way `_rotation_gate` reuses it for single-target field
    rotation — `pos.alt_deg` in the result is the *centroid's* altitude,
    not any real member's; callers needing a member's own altitude (e.g.
    the group's worst-wins score) recompute it at the returned time.
    """
    anchor = grouping.centroid_target(members)
    return constraints.best_time_tonight(
        site, anchor, when, extra_ok=_group_gate(rig, site, members)
    )


def _build_ranked_group(
    site: Site, rig: Rig, members: tuple[Target, ...], when: datetime
) -> RankedGroup | None:
    """A `RankedGroup` for `members`, or None if they have no shared
    observable moment tonight (see `_group_best_time`)."""
    result = _group_best_time(site, rig, members, when)
    if result is None:
        return None
    best_time, centroid_pos = result

    worst_alt_deg = min(
        ephemeris.altaz(site, member, best_time).alt_deg for member in members
    )
    pos = ephemeris.AltAz(
        alt_deg=worst_alt_deg,
        az_deg=centroid_pos.az_deg,
        distance_au=centroid_pos.distance_au,
    )
    fit = grouping.group_framing_score(rig, members)
    reach = min(
        framing.reach_factor(site, member.magnitude, member.size_arcmin)
        for member in members
    )
    return RankedGroup(targets=members, best_time=best_time, pos=pos, fit=fit, reach=reach)


def _fold_in_groups(
    site: Site, rig: Rig, ranked: list[RankedTarget], when: datetime
) -> list[RankedEntry]:
    """Replace each co-visible group's member `RankedTarget`s (see
    `engine.grouping.find_groups`) with one combined `RankedGroup`, for
    every group that also turns out simultaneously observable tonight —
    angular closeness alone doesn't guarantee that (see
    `_group_best_time`). Ungrouped targets, and groups that fail the
    simultaneous check, pass through unchanged.
    """
    by_target = {row.target: row for row in ranked}
    groups = grouping.find_groups(rig, [row.target for row in ranked])

    entries: list[RankedEntry] = []
    grouped_targets: set[Target] = set()
    for members in groups:
        ranked_group = _build_ranked_group(site, rig, members, when)
        if ranked_group is None:
            continue
        entries.append(ranked_group)
        grouped_targets.update(members)

    entries.extend(
        row for target, row in by_target.items() if target not in grouped_targets
    )
    entries.sort(
        key=lambda row: framing.target_priority_score(row.pos.alt_deg, row.fit, row.reach),
        reverse=True,
    )
    return entries


def rank_targets(
    site: Site,
    rig: Rig,
    when: datetime,
    types: frozenset[TargetType] | None = None,
    limit: int | None = None,
) -> list[RankedEntry]:
    """Rank catalog targets by their best moment within tonight's dark window.

    A target is dropped unless some moment tonight simultaneously clears
    altitude, astronomical night, moon separation, the site's horizon
    profile, and — for alt-az rigs only — safe field rotation near the
    zenith (see `engine.constraints.best_time_tonight` / `engine.framing`).
    Each row also carries a framing score (0..1): how well the target's
    angular size fits `rig`'s field of view.

    `types`, if given, keeps only targets carrying at least one of those
    categories (e.g. `{"galaxy"}`) — None means no filtering.

    `limit`, if given, caps the number of catalog targets that are
    *evaluated* (not the number returned).  `0` means unlimited.
    `None` falls back to `DEFAULT_MAX_EVALUATED`.  Targets past the limit
    are skipped before the expensive ephemeris check, keeping `lotse plan`
    fast even with a large catalog.  The first N matching objects are
    evaluated (catalog order is magnitude-binned, brightest first).

    Ranked by `framing.target_priority_score` (altitude, fit, and
    surface-brightness reach together), not altitude alone — a target
    that barely fits the frame, or is too diffuse for this site's sky
    darkness, no longer wins purely for sitting high in the sky.

    Targets close enough to share one frame of `rig` (see
    `engine.grouping`) and simultaneously observable tonight are folded
    into a single `RankedGroup`, replacing their individual `RankedTarget`
    entries — see `_fold_in_groups`.
    """
    if limit is None:
        limit = DEFAULT_MAX_EVALUATED
    ranked: list[RankedTarget] = []
    evaluated = 0
    for target in CATALOG:
        if types is not None and not (set(target.types) & types):
            continue
        if 0 < limit <= evaluated:
            break
        evaluated += 1
        result = constraints.best_time_tonight(
            site, target, when, extra_ok=_rotation_gate(rig, site, target)
        )
        if result is None:
            continue
        best_time, pos = result
        reach = framing.reach_factor(site, target.magnitude, target.size_arcmin)
        ranked.append(
            RankedTarget(
                target, best_time, pos, framing.framing_score(rig, target), reach
            )
        )
    ranked.sort(
        key=lambda row: framing.target_priority_score(row.pos.alt_deg, row.fit, row.reach),
        reverse=True,
    )
    return _fold_in_groups(site, rig, ranked, when)


class RankedTargetForBestRig(NamedTuple):
    """One catalog target's best moment tonight with whichever configured
    rig frames it best — `rank_targets_for_best_rig`'s result row, the
    best-rig-chooser counterpart to `RankedTarget`.
    """

    target: Target
    rig: Rig
    best_time: datetime
    pos: ephemeris.AltAz
    fit: float
    reach: float


def rank_targets_for_best_rig(
    site: Site,
    rigs: list[Rig],
    when: datetime,
    types: frozenset[TargetType] | None = None,
    limit: int | None = None,
) -> list[RankedTargetForBestRig]:
    """The best-rig chooser: for each target, evaluate every rig in
    `rigs` and keep only the one that scores highest
    (`framing.target_priority_score`) — rather than `rank_targets`,
    which requires one rig for the whole run.

    `types` and `limit` behave exactly as in `rank_targets` — filtering
    and the evaluated-target cap are unaffected by having multiple rigs
    to check per target; `limit` still counts catalog targets, not
    (target, rig) attempts.

    Multi-object grouping (`engine.grouping`, see `rank_targets`) isn't
    applied here: a co-visible group only makes sense for one shared
    rig's field of view, but two targets in this mode can each win with
    a *different* rig, leaving no single field of view to group against.
    Choosing a best rig per target first, then grouping among whatever
    wins under a shared rig, is a possible future refinement (see
    ROADMAP.md's best-rig-chooser item), not attempted here.
    """
    if limit is None:
        limit = DEFAULT_MAX_EVALUATED
    ranked: list[RankedTargetForBestRig] = []
    evaluated = 0
    for target in CATALOG:
        if types is not None and not (set(target.types) & types):
            continue
        if 0 < limit <= evaluated:
            break
        evaluated += 1

        best_for_target: RankedTargetForBestRig | None = None
        for rig in rigs:
            result = constraints.best_time_tonight(
                site, target, when, extra_ok=_rotation_gate(rig, site, target)
            )
            if result is None:
                continue
            best_time, pos = result
            reach = framing.reach_factor(site, target.magnitude, target.size_arcmin)
            candidate = RankedTargetForBestRig(
                target, rig, best_time, pos, framing.framing_score(rig, target), reach
            )
            if best_for_target is None or framing.target_priority_score(
                candidate.pos.alt_deg, candidate.fit, candidate.reach
            ) > framing.target_priority_score(
                best_for_target.pos.alt_deg,
                best_for_target.fit,
                best_for_target.reach,
            ):
                best_for_target = candidate

        if best_for_target is not None:
            ranked.append(best_for_target)

    ranked.sort(
        key=lambda row: framing.target_priority_score(row.pos.alt_deg, row.fit, row.reach),
        reverse=True,
    )
    return ranked


def fetch_weather_summary(
    site: Site, evening_start: datetime, morning_end: datetime
) -> WeatherSummary | None:
    """Weather for `site`'s dark window on the planned night, or None if
    unreachable.

    Weather is an optional layer (see CLAUDE.md's Leitprinzip): any
    failure here — no network, a bad response — must not stop planning
    from producing a ranking, just narrow the verdict to sky geometry
    alone.
    """
    try:
        hours = open_meteo.fetch_hourly_cached(site.lat_deg, site.lon_deg)
    except open_meteo.WeatherUnavailable:
        return None
    return open_meteo.summarize_window(hours, evening_start, morning_end)


def _moon_rise_set(
    site: Site, evening_start: datetime, morning_end: datetime
) -> tuple[datetime | None, datetime | None]:
    """The first moonrise and first moonset within the dark window, or
    None for either that doesn't occur in it (the Moon already up at
    evening_start and not setting before morning_end, for example)."""
    events = ephemeris.moon_rise_set_events(site, evening_start, morning_end)
    rise = next((when for when, is_rising in events if is_rising), None)
    set_ = next((when for when, is_rising in events if not is_rising), None)
    return rise, set_


def plan_night(
    site: Site,
    rig: Rig,
    when: datetime,
    types: frozenset[TargetType] | None = None,
    limit: int | None = None,
) -> NightPlan:
    """Rank tonight's (or `when`'s night's) observable targets and verdict.

    `types` is passed straight through to `rank_targets` — see there.
    `limit` is passed straight through to `rank_targets` — see there.
    """
    evening_start, morning_end = constraints.dark_window(site, when)
    illumination_pct = moon_illumination(Time(when)) * 100
    moonrise, moonset = _moon_rise_set(site, evening_start, morning_end)
    weather = fetch_weather_summary(site, evening_start, morning_end)
    ranked = rank_targets(site, rig, when, types=types, limit=limit)

    shortlist = [
        ShortlistEntry(row, scoring.verdict_for_target(row.pos.alt_deg, weather=weather))
        for row in ranked[:SHORTLIST_SIZE]
    ]

    return NightPlan(
        site=site,
        rig=rig,
        evening_start=evening_start,
        morning_end=morning_end,
        moon_illumination_pct=illumination_pct,
        moonrise=moonrise,
        moonset=moonset,
        weather=weather,
        ranked=ranked,
        shortlist=shortlist,
    )


class BestRigShortlistEntry(NamedTuple):
    """One shortlisted target with its own GO/MARGINAL/SKIP verdict, for
    the best-rig chooser — see `ShortlistEntry`."""

    ranked: RankedTargetForBestRig
    verdict: Verdict


@dataclass(frozen=True)
class NightPlanForBestRig:
    """`NightPlan`'s best-rig-chooser counterpart: no single `rig` field,
    since each ranked entry can win with a different one — see
    `rank_targets_for_best_rig`.
    """

    site: Site
    evening_start: datetime
    morning_end: datetime
    moon_illumination_pct: float
    moonrise: datetime | None
    moonset: datetime | None
    weather: WeatherSummary | None
    ranked: list[RankedTargetForBestRig]
    shortlist: list[BestRigShortlistEntry]


def plan_night_for_best_rig(
    site: Site,
    rigs: list[Rig],
    when: datetime,
    types: frozenset[TargetType] | None = None,
    limit: int | None = None,
) -> NightPlanForBestRig:
    """`plan_night`'s best-rig-chooser counterpart — see
    `rank_targets_for_best_rig` for what's different (a rig chosen per
    target instead of one for the whole plan; no grouping).
    """
    evening_start, morning_end = constraints.dark_window(site, when)
    illumination_pct = moon_illumination(Time(when)) * 100
    moonrise, moonset = _moon_rise_set(site, evening_start, morning_end)
    weather = fetch_weather_summary(site, evening_start, morning_end)
    ranked = rank_targets_for_best_rig(site, rigs, when, types=types, limit=limit)

    shortlist = [
        BestRigShortlistEntry(
            row, scoring.verdict_for_target(row.pos.alt_deg, weather=weather)
        )
        for row in ranked[:SHORTLIST_SIZE]
    ]

    return NightPlanForBestRig(
        site=site,
        evening_start=evening_start,
        morning_end=morning_end,
        moon_illumination_pct=illumination_pct,
        moonrise=moonrise,
        moonset=moonset,
        weather=weather,
        ranked=ranked,
        shortlist=shortlist,
    )

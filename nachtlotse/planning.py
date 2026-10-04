"""Night planning — orchestrates engine, data, and weather into one result.

Sits between the pure `engine` core and any UI. `cli.py` calls
`plan_night()` instead of duplicating this pipeline — a future UI would
do the same, rather than the ranking logic or weather fetch living
twice. This module itself is not UI: no printing, no framework imports
— that's what keeps it shared.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import NamedTuple

from astroplan import moon_illumination
from astropy.time import Time

from nachtlotse.data.catalog import CATALOG
from nachtlotse.engine import (
    comets,
    constraints,
    ephemeris,
    framing,
    grouping,
    scoring,
)
from nachtlotse.engine.models import (
    Darkness,
    EventKind,
    Rig,
    Site,
    Target,
    TargetType,
    Verdict,
    WeatherSummary,
)
from nachtlotse.events import EventsUnavailable, cobs, mpc, rochester, tns
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
    # Same source data `weather` summarizes into one max/avg number, kept
    # hour-by-hour instead (see `fetch_hourly_cloud_cover`) — empty list,
    # not None, when weather is unreachable (a chart with zero points
    # already reads as "nothing to show").
    hourly_cloud_cover: list[open_meteo.HourlyWeather]
    ranked: list[RankedEntry]
    # The top SHORTLIST_SIZE of `ranked`, each with its own verdict, plus
    # any favorite entries that didn't already make that cutoff — see
    # `_fold_favorites_into_shortlist`; can run longer than SHORTLIST_SIZE
    # when a favorite is why. Empty only when no catalog target clears
    # constraints tonight at all.
    shortlist: list[ShortlistEntry]
    # "nautical" on a night without astronomical darkness (midsummer) —
    # see `constraints.dark_window`; verdicts are capped accordingly.
    darkness: Darkness = "astronomical"
    # Current events tonight (comets, ...) — None unless asked for
    # (`plan_night(..., include_events=True)`), see `current_events`.
    events: EventsReport | None = None


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


def best_time_for(
    site: Site, rig: Rig, targets: tuple[Target, ...], when: datetime
) -> tuple[datetime, ephemeris.AltAz] | None:
    """The moment `rank_targets` would pick for one target, or for a group
    sharing one frame — the same constraint checks and rotation gate, for
    callers (e.g. `lotse frame`) asking about specific targets rather
    than ranking the catalog. None if there's no such moment tonight."""
    if len(targets) == 1:
        (target,) = targets
        return constraints.best_time_tonight(
            site, target, when, extra_ok=_rotation_gate(rig, site, target)
        )
    return _group_best_time(site, rig, targets, when)


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
    return RankedGroup(
        targets=members, best_time=best_time, pos=pos, fit=fit, reach=reach
    )


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
        key=lambda row: framing.target_priority_score(
            row.pos.alt_deg, row.fit, row.reach
        ),
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
    `Target.favorite` entries are exempt from this cap — they're always
    evaluated, wherever they sit in catalog order, so a low `limit` can
    never make a favorite silently vanish from the plan (only the actual
    tonight-visibility checks in `constraints.best_time_tonight` can drop
    one). They don't count against `limit` either, so a small `limit`
    plus a favorite never costs headroom meant for other objects.

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
        # Favorites are exempt from the cap (see docstring) — can't just
        # `break` once the limit's hit, since a favorite may still be
        # further down catalog order; keep scanning, just without paying
        # for the expensive ephemeris check on anything else past it.
        if not target.favorite:
            if 0 < limit <= evaluated:
                continue
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
        key=lambda row: framing.target_priority_score(
            row.pos.alt_deg, row.fit, row.reach
        ),
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
        # Favorites are exempt from the cap — see `rank_targets`'s
        # docstring for why this can't just `break` once the limit's hit.
        if not target.favorite:
            if 0 < limit <= evaluated:
                continue
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
        key=lambda row: framing.target_priority_score(
            row.pos.alt_deg, row.fit, row.reach
        ),
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


def fetch_hourly_cloud_cover(
    site: Site, evening_start: datetime, morning_end: datetime
) -> list[open_meteo.HourlyWeather]:
    """Cloud cover, hour by hour, clipped to the dark window — see
    ROADMAP.md's "Hourly cloud cover for the astro-night". `open_meteo.
    fetch_hourly_cached` means this costs no extra network round-trip
    when `fetch_weather_summary` already fetched the same site this
    hour.

    Same offline-safe contract as `fetch_weather_summary`: unreachable
    weather is an empty list, not an exception — this is a display
    refinement, never something the ranking itself depends on.
    """
    try:
        hours = open_meteo.fetch_hourly_cached(site.lat_deg, site.lon_deg)
    except open_meteo.WeatherUnavailable:
        return []
    return open_meteo.hourly_forecast_in_window(hours, evening_start, morning_end)


def _entry_targets(entry: object) -> tuple[Target, ...]:
    """The one or more real catalog targets behind a ranked entry — a
    `RankedGroup`'s members, or a single-target entry's own target.
    Works for `RankedTargetForBestRig` too (same `.target` shape as
    `RankedTarget`), so `is_favorite` below covers both `plan_night` and
    `plan_night_for_best_rig`."""
    if isinstance(entry, RankedGroup):
        return entry.targets
    return (entry.target,)  # type: ignore[attr-defined]


def is_favorite(entry: object) -> bool:
    """Whether any real target behind this ranked entry is starred
    (`Target.favorite`) — a `RankedGroup` counts if any member does."""
    return any(target.favorite for target in _entry_targets(entry))


def _fold_favorites_into_shortlist(ranked: list) -> list:
    """The top `SHORTLIST_SIZE` ranked entries, plus any favorite entries
    that didn't already make that cut (ROADMAP.md's "Favorites in the
    catalog": a favorite should keep showing up regardless of where its
    current score would otherwise leave it, e.g. T CrB's fit score is
    always ~0 since it's a point source).

    Doesn't reorder anything: favorites beyond the cutoff are appended
    after it, in their own ranked order — never promoted above a
    higher-scoring non-favorite entry, and the top `SHORTLIST_SIZE`
    themselves are always exactly `ranked[:SHORTLIST_SIZE]`, whether or
    not any of them happen to be favorites too.
    """
    top = ranked[:SHORTLIST_SIZE]
    extra_favorites = [entry for entry in ranked[SHORTLIST_SIZE:] if is_favorite(entry)]
    return top + extra_favorites


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
    *,
    include_events: bool = False,
) -> NightPlan:
    """Rank tonight's (or `when`'s night's) observable targets and verdict.

    `types` is passed straight through to `rank_targets` — see there.
    `limit` is passed straight through to `rank_targets` — see there.
    `include_events` also gathers tonight's current events
    (`current_events` — network, cached, never fatal); off by default, so
    a plan never reaches out to event sources unless a front end asks.
    """
    evening_start, morning_end = constraints.dark_window(site, when)
    darkness = constraints.darkness(site, when)
    illumination_pct = moon_illumination(Time(when)) * 100
    moonrise, moonset = _moon_rise_set(site, evening_start, morning_end)
    weather = fetch_weather_summary(site, evening_start, morning_end)
    hourly_cloud_cover = fetch_hourly_cloud_cover(site, evening_start, morning_end)
    ranked = rank_targets(site, rig, when, types=types, limit=limit)

    shortlist = [
        ShortlistEntry(
            row,
            scoring.verdict_for_target(
                row.pos.alt_deg, weather=weather, darkness=darkness
            ),
        )
        for row in _fold_favorites_into_shortlist(ranked)
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
        hourly_cloud_cover=hourly_cloud_cover,
        ranked=ranked,
        shortlist=shortlist,
        darkness=darkness,
        events=(
            current_events(site, rig, when, weather=weather, darkness=darkness)
            if include_events
            else None
        ),
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
    hourly_cloud_cover: list[open_meteo.HourlyWeather]
    ranked: list[RankedTargetForBestRig]
    shortlist: list[BestRigShortlistEntry]
    # "nautical" on a night without astronomical darkness (midsummer) —
    # see `constraints.dark_window`; verdicts are capped accordingly.
    darkness: Darkness = "astronomical"


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
    darkness = constraints.darkness(site, when)
    illumination_pct = moon_illumination(Time(when)) * 100
    moonrise, moonset = _moon_rise_set(site, evening_start, morning_end)
    weather = fetch_weather_summary(site, evening_start, morning_end)
    hourly_cloud_cover = fetch_hourly_cloud_cover(site, evening_start, morning_end)
    ranked = rank_targets_for_best_rig(site, rigs, when, types=types, limit=limit)

    shortlist = [
        BestRigShortlistEntry(
            row,
            scoring.verdict_for_target(
                row.pos.alt_deg, weather=weather, darkness=darkness
            ),
        )
        for row in _fold_favorites_into_shortlist(ranked)
    ]

    return NightPlanForBestRig(
        site=site,
        evening_start=evening_start,
        morning_end=morning_end,
        moon_illumination_pct=illumination_pct,
        moonrise=moonrise,
        moonset=moonset,
        weather=weather,
        hourly_cloud_cover=hourly_cloud_cover,
        ranked=ranked,
        shortlist=shortlist,
        darkness=darkness,
    )


# --- Current events (ROADMAP.md) ---------------------------------------------


# How far a planned night may lie from the event data (before or after)
# for "current" to still mean anything: observed comet brightness drifts
# over weeks, and a night far off is better served by no list than by a
# misleading one. The same span as COBS's own reporting window.
EVENTS_HORIZON_DAYS = 14


class RankedEvent(NamedTuple):
    """A current event that's a candidate tonight: observable (the same
    constraints as any catalog target) and bright enough for the rig
    (`framing.event_limiting_magnitude`)."""

    kind: EventKind
    # A fixed snapshot — for a comet, its position at the middle of the
    # dark window (see `engine.comets`), with its observed magnitude and
    # coma diameter as size when known.
    target: Target
    best_time: datetime
    pos: ephemeris.AltAz
    fit: float
    reach: float
    verdict: Verdict
    # Where the magnitude comes from, for display — e.g. "COBS: median of
    # 23 reports, latest 2026-10-03".
    magnitude_source: str
    # Comets only: how fast it moves against the stars (deg/h).
    motion_deg_per_hour: float | None


class SkippedEvent(NamedTuple):
    """A current event that didn't make it tonight, and why — for a full
    listing (`lotse events`), never for the plan itself."""

    kind: EventKind
    name: str
    magnitude: float | None
    reason: str


@dataclass(frozen=True)
class EventsReport:
    # Ranked like the catalog (`framing.target_priority_score`).
    events: list[RankedEvent]
    skipped: list[SkippedEvent]
    # Data provenance and gaps, in plain words — e.g. "COBS observations
    # from 2026-10-04 09:12 UTC", "MPC comet orbits unavailable (offline)".
    notes: list[str]


def current_events(
    site: Site,
    rig: Rig,
    when: datetime,
    *,
    weather: WeatherSummary | None = None,
    darkness: Darkness = "astronomical",
) -> EventsReport:
    """Tonight's current events for `site`/`rig`, verdicted like catalog
    targets (`weather` and `darkness` as for `plan_night`'s own shortlist):

    - comets observed in the last two weeks (COBS) with a known orbit
      (MPC), positioned by the engine;
    - supernovae and extragalactic novae on Rochester's list of active
      bright transients (current magnitudes), positioned and typed by TNS;
    - recent novae from TNS, listed with their discovery magnitude when no
      current brightness is known.

    Each is filtered by the rig's brightness limit and tonight's
    observability. Never raises for a missing source: what couldn't be
    fetched becomes a note, and the report is simply shorter (or empty).
    """
    night = _EventNight(site, rig, when, weather, darkness)
    ranked: list[RankedEvent] = []
    skipped: list[SkippedEvent] = []
    notes: list[str] = []
    for section in (_comet_events, _transient_events):
        section_ranked, section_skipped, section_notes = section(night)
        ranked += section_ranked
        skipped += section_skipped
        notes += section_notes

    # Altitude and reach only: unlike a catalog object, an event's size
    # isn't something to choose between — a comet's coma is a few arcmin
    # in any rig's field, a supernova a point — so `fit` (still reported,
    # for framing) would just reorder events by apparent size.
    ranked.sort(
        key=lambda e: framing.target_priority_score(e.pos.alt_deg, 1.0, e.reach),
        reverse=True,
    )
    skipped.sort(key=lambda s: (s.magnitude is None, s.magnitude or 0.0))
    return EventsReport(ranked, skipped, notes)


class _EventNight:
    """What every current-events section needs about the night planned."""

    def __init__(
        self,
        site: Site,
        rig: Rig,
        when: datetime,
        weather: WeatherSummary | None,
        darkness: Darkness,
    ) -> None:
        self.site = site
        self.rig = rig
        self.when = when
        self.weather = weather
        self.darkness = darkness
        self.evening_start, self.morning_end = constraints.dark_window(site, when)

    def too_far_from(self, data_time: datetime) -> str | None:
        """A note if this night lies more than `EVENTS_HORIZON_DAYS` from
        when the data was fetched, else None."""
        if abs(self.evening_start - data_time) <= timedelta(days=EVENTS_HORIZON_DAYS):
            return None
        return (
            "Current events only cover nights within "
            f"{EVENTS_HORIZON_DAYS} days of today — this one is "
            f"{self.evening_start:%Y-%m-%d}."
        )

    def rank(
        self,
        kind: EventKind,
        target: Target,
        magnitude_source: str,
        motion_deg_per_hour: float | None = None,
    ) -> RankedEvent | SkippedEvent:
        """`target` ranked for tonight, or skipped with the reason — too
        faint for the rig here, or not observable."""
        assert target.magnitude is not None
        limit_mag = framing.event_limiting_magnitude(self.rig, self.site, kind)
        if limit_mag is not None and target.magnitude > limit_mag:
            return SkippedEvent(
                kind,
                target.name,
                target.magnitude,
                f"too faint for this rig here (limit {limit_mag:.1f} mag)",
            )
        best = best_time_for(self.site, self.rig, (target,), self.when)
        if best is None:
            return SkippedEvent(
                kind,
                target.name,
                target.magnitude,
                "not observable tonight (altitude, horizon, moon, or rotation)",
            )
        best_time, pos = best
        return RankedEvent(
            kind=kind,
            target=target,
            best_time=best_time,
            pos=pos,
            fit=framing.framing_score(self.rig, target),
            reach=framing.reach_factor(self.site, target.magnitude, target.size_arcmin),
            verdict=scoring.verdict_for_target(
                pos.alt_deg, weather=self.weather, darkness=self.darkness
            ),
            magnitude_source=magnitude_source,
            motion_deg_per_hour=motion_deg_per_hour,
        )


_Section = tuple[list[RankedEvent], list[SkippedEvent], list[str]]


def _split(results: list[RankedEvent | SkippedEvent]) -> tuple[list, list]:
    ranked = [r for r in results if isinstance(r, RankedEvent)]
    skipped = [r for r in results if isinstance(r, SkippedEvent)]
    return ranked, skipped


def _comet_events(night: _EventNight) -> _Section:
    try:
        orbits = mpc.fetch_comet_orbits()
        brightness = cobs.fetch_comet_brightness()
    except EventsUnavailable as exc:
        return [], [], [f"Comets unavailable: {exc}"]
    too_far = night.too_far_from(brightness.fetched_at)
    if too_far:
        return [], [], [too_far]

    snapshot_time = night.evening_start + (night.morning_end - night.evening_start) / 2
    results: list[RankedEvent | SkippedEvent] = []
    for observed in brightness.comets.values():
        orbit = orbits.orbits.get(observed.mpc_key)
        if orbit is None:
            results.append(
                SkippedEvent(
                    "comet",
                    observed.designation,
                    observed.magnitude,
                    "no MPC comet orbit (e.g. filed as an asteroid)",
                )
            )
            continue
        coma_arcmin = observed.coma_diameter_arcmin or 0.0
        target = replace(
            comets.comet_target(orbit, night.site, snapshot_time),
            magnitude=observed.magnitude,
            size_arcmin=(coma_arcmin, coma_arcmin),
        )
        result = night.rank(
            "comet",
            target,
            magnitude_source=(
                f"COBS: median of {observed.report_count} report"
                f"{'' if observed.report_count == 1 else 's'}, latest "
                f"{observed.last_reported:%Y-%m-%d}"
            ),
        )
        if isinstance(result, RankedEvent):
            result = result._replace(
                motion_deg_per_hour=comets.sky_motion_deg_per_hour(
                    orbit, night.site, result.best_time
                )
            )
        results.append(result)

    ranked, skipped = _split(results)
    return (
        ranked,
        skipped,
        [
            f"Comet orbits: MPC, {orbits.fetched_at:%Y-%m-%d %H:%M} UTC",
            (
                f"Comet brightness: COBS reports of the last "
                f"{brightness.window_days} days, "
                f"{brightness.fetched_at:%Y-%m-%d %H:%M} UTC"
            ),
        ],
    )


def _transient_events(night: _EventNight) -> _Section:
    try:
        brightness = rochester.fetch_transient_brightness()
    except EventsUnavailable as exc:
        return [], [], [f"Supernovae unavailable: {exc}"]
    too_far = night.too_far_from(brightness.fetched_at)
    if too_far:
        return [], [], []  # the comet section already says so

    results: list[RankedEvent | SkippedEvent] = []
    to_locate: list[str] = []
    for item in brightness.transients.values():
        kind: EventKind = "nova" if item.rochester_type == "EGN" else "supernova"
        if item.rochester_type == "unk":
            results.append(
                SkippedEvent(
                    "supernova",
                    f"AT {item.objname}",
                    item.magnitude,
                    "unclassified transient (not yet a confirmed supernova or nova)",
                )
            )
        elif item.stale:
            results.append(
                SkippedEvent(
                    kind,
                    f"{'AT' if kind == 'nova' else 'SN'} {item.objname}",
                    item.magnitude,
                    "last brightness report over a month old",
                )
            )
        else:
            to_locate.append(item.objname)

    # Positions normally come with Rochester's list; TNS only for the rest.
    records = tns.lookup_objects(
        [n for n in to_locate if brightness.transients[n].ra_deg is None]
    )
    for objname in to_locate:
        item = brightness.transients[objname]
        if item.ra_deg is not None and item.dec_deg is not None:
            kind = "nova" if item.rochester_type == "EGN" else "supernova"
            label = (
                "nova"
                if kind == "nova"
                else f"SN {item.rochester_type}".removesuffix(" ")
            )
            host = f" in {item.host}" if item.host else ""
            target = Target(
                name=f"{'AT' if kind == 'nova' else 'SN'} {objname}",
                ra_deg=item.ra_deg,
                dec_deg=item.dec_deg,
                magnitude=item.magnitude,
                types=(kind,),
            )
            results.append(
                night.rank(
                    kind,
                    target,
                    magnitude_source=(
                        f"Rochester list {brightness.fetched_at:%Y-%m-%d}; "
                        f"{label}{host}"
                    ),
                )
            )
            continue
        record = records.get(objname)
        if record is None:
            is_nova = item.rochester_type == "EGN"
            results.append(
                SkippedEvent(
                    "nova" if is_nova else "supernova",
                    f"{'AT' if is_nova else 'SN'} {objname}",
                    item.magnitude,
                    "position not known yet (TNS lookups are rate-limited — "
                    "a later plan fills it in)",
                )
            )
            continue
        kind = "nova" if record.tns_type == "Nova" else "supernova"
        host = f" in {record.host}" if record.host else ""
        target = Target(
            name=record.name,
            ra_deg=record.ra_deg,
            dec_deg=record.dec_deg,
            magnitude=item.magnitude,
            types=(kind,),
        )
        results.append(
            night.rank(
                kind,
                target,
                magnitude_source=(
                    f"Rochester list {brightness.fetched_at:%Y-%m-%d}; "
                    f"{record.tns_type}{host}"
                ),
            )
        )

    notes = [
        (
            "Supernova/nova brightness: Rochester 'Latest Supernovae', "
            f"{brightness.fetched_at:%Y-%m-%d %H:%M} UTC (positions from its "
            "links, else TNS); recent novae: TNS"
        )
    ]
    try:
        novae = tns.fetch_recent_novae()
    except EventsUnavailable as exc:
        notes.append(f"Recent novae unavailable: {exc}")
    else:
        for nova in novae.novae:
            if nova.objname in brightness.transients:
                continue  # already handled with its current magnitude
            discovered = f"discovered {nova.discovery_date[:10]}" + (
                f" at {nova.discovery_mag:.1f} mag"
                if nova.discovery_mag is not None
                else ""
            )
            results.append(
                SkippedEvent(
                    "nova",
                    nova.name,
                    None,
                    f"no current brightness report ({discovered}"
                    f"{', in ' + nova.host if nova.host else ''})",
                )
            )

    ranked, skipped = _split(results)
    return ranked, skipped, notes


def _event_name_keys(name: str) -> set[str]:
    """The ways a user might type an event's name, normalized: the full
    name ("C/2026 A2 (Bok)"), without the discoverer ("C/2026 A2"), for a
    numbered periodic comet its number alone ("161P" for
    "161P/Hartley-IRAS"), and for a supernova or nova its TNS name without
    prefix ("2026aaiv" for "SN 2026aaiv")."""

    def norm(text: str) -> str:
        return "".join(text.split()).casefold()

    keys = {norm(name), norm(name.split(" (")[0])}
    head = name.split("/")[0]
    if head[:-1].isdigit():
        keys.add(norm(head))
    # "SN 2026aaiv" / "AT 2026aaom" also answer to their bare TNS name.
    if name[:3] in ("SN ", "AT "):
        keys.add(norm(name[3:]))
    return keys


def find_event(report: EventsReport, query: str) -> RankedEvent | SkippedEvent | None:
    """The event in `report` that `query` names (see `_event_name_keys`)
    — a ranked one first, else a skipped one (whose reason then says why
    it isn't worth shooting tonight), else None."""
    wanted = "".join(query.split()).casefold()
    for event in report.events:
        if wanted in _event_name_keys(event.target.name):
            return event
    for skipped in report.skipped:
        if wanted in _event_name_keys(skipped.name):
            return skipped
    return None

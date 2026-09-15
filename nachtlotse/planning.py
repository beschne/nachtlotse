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
from nachtlotse.engine import constraints, ephemeris, framing, scoring
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


class ShortlistEntry(NamedTuple):
    """One shortlisted target with its own GO/MARGINAL/SKIP verdict.

    There is no single hero target and no single verdict for the night —
    each of the top few ranked targets is independently judged on its own
    altitude (see `engine.scoring.verdict_for_target`), so a night can be a
    GO on one target and a SKIP on another.
    """

    ranked: RankedTarget
    verdict: Verdict


# How many of the top-ranked targets get their own verdict. A "handful", per
# the roadmap — not the whole ranking, which can run to dozens of targets.
SHORTLIST_SIZE = 5


@dataclass(frozen=True)
class NightPlan:
    """Everything needed to render a plan, independent of any UI."""

    site: Site
    rig: Rig
    evening_start: datetime
    morning_end: datetime
    moon_illumination_pct: float
    weather: WeatherSummary | None
    ranked: list[RankedTarget]
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


def rank_targets(
    site: Site,
    rig: Rig,
    when: datetime,
    types: frozenset[TargetType] | None = None,
) -> list[RankedTarget]:
    """Rank catalog targets by their best moment within tonight's dark window.

    A target is dropped unless some moment tonight simultaneously clears
    altitude, astronomical night, moon separation, the site's horizon
    profile, and — for alt-az rigs only — safe field rotation near the
    zenith (see `engine.constraints.best_time_tonight` / `engine.framing`).
    Each row also carries a framing score (0..1): how well the target's
    angular size fits `rig`'s field of view.

    `types`, if given, keeps only targets carrying at least one of those
    categories (e.g. `{"galaxy"}`) — None means no filtering.

    Ranked by `framing.target_priority_score` (altitude, fit, and
    surface-brightness reach together), not altitude alone — a target
    that barely fits the frame, or is too diffuse for this site's sky
    darkness, no longer wins purely for sitting high in the sky.
    """
    ranked: list[RankedTarget] = []
    for target in CATALOG:
        if types is not None and not (set(target.types) & types):
            continue
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


def plan_night(
    site: Site,
    rig: Rig,
    when: datetime,
    types: frozenset[TargetType] | None = None,
) -> NightPlan:
    """Rank tonight's (or `when`'s night's) observable targets and verdict.

    `types` is passed straight through to `rank_targets` — see there.
    """
    evening_start, morning_end = constraints.dark_window(site, when)
    illumination_pct = moon_illumination(Time(when)) * 100
    weather = fetch_weather_summary(site, evening_start, morning_end)
    ranked = rank_targets(site, rig, when, types=types)

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
        weather=weather,
        ranked=ranked,
        shortlist=shortlist,
    )

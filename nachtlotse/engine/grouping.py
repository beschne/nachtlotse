"""Multi-object grouping — which catalog targets share one frame?

Purely geometric and time-independent, like `framing.framing_score`: two
catalog targets' RA/Dec never move, so "would they fit in one shot of this
rig" doesn't depend on when you'd shoot it (unlike moon separation, which
does — see `constraints.moon_separation_deg`). Whether a group is
*simultaneously observable tonight* is a separate, time-dependent question
answered in `planning.py`, which is where this module's output — a
grouping of already-ranked targets — actually gets used.

A group's "size" for framing purposes is `group_span_arcmin`: the largest
pairwise separation among its members. That's also exactly what
`co_visible_group` checks against `framing.fov_short_arcmin(rig)` — if
the two farthest-apart members fit, every closer pair fits too.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence

from astropy import units as u
from astropy.coordinates import SkyCoord

from nachtlotse.engine import framing
from nachtlotse.engine.models import Rig, Target


def angular_separation_deg(a: Target, b: Target) -> float:
    """Angular separation between two catalog targets' fixed positions.

    Static geometry — no site or time involved, unlike
    `constraints.moon_separation_deg`, which tracks a moving body.
    """
    coord_a = SkyCoord(ra=a.ra_deg * u.deg, dec=a.dec_deg * u.deg, frame="icrs")
    coord_b = SkyCoord(ra=b.ra_deg * u.deg, dec=b.dec_deg * u.deg, frame="icrs")
    return float(coord_a.separation(coord_b).deg)


def group_span_arcmin(targets: Sequence[Target]) -> float:
    """The largest pairwise separation among `targets`, in arcmin.

    A group's own "size" for framing-fit purposes (see
    `group_framing_score`) and the exact quantity `co_visible_group`
    checks against the rig's field of view. 0.0 for fewer than two
    targets.
    """
    pairs = itertools.combinations(targets, 2)
    return max((angular_separation_deg(a, b) * 60.0 for a, b in pairs), default=0.0)


def co_visible_group(rig: Rig, targets: Sequence[Target]) -> bool:
    """Whether every member of `targets` fits together in one frame of
    `rig`, regardless of how an alt-az mount's field rotation orients
    the frame during the session.

    Checking the largest pairwise separation against
    `framing.fov_short_arcmin(rig)` (the rotation-invariant bound) is
    equivalent to checking every pair individually — if the two
    farthest-apart members fit, every closer pair does too.
    """
    if len(targets) < 2:
        return True
    return group_span_arcmin(targets) <= framing.fov_short_arcmin(rig)


def group_framing_score(rig: Rig, targets: Sequence[Target]) -> float:
    """How well a co-visible group's own angular footprint fits `rig`'s
    field of view — `framing.fill_fraction_score`'s fade curve, fed the
    group's own span (`group_span_arcmin`) instead of one target's size.
    """
    return framing.fill_fraction_score(
        group_span_arcmin(targets), framing.fov_short_arcmin(rig)
    )


def find_groups(rig: Rig, candidates: Sequence[Target]) -> list[tuple[Target, ...]]:
    """Cluster `candidates` into non-overlapping co-visible groups of
    two or more, preserving `candidates`' own order (already
    priority-ranked by the caller — see `planning.rank_targets`).

    Greedy, not an exhaustive maximal-clique search: walks `candidates`
    in order, and for each unclaimed target greedily absorbs every
    later unclaimed target that stays co-visible with the whole group
    formed so far. Deterministic and cheap at this project's catalog
    scale (see `planning.DEFAULT_MAX_EVALUATED`); may occasionally miss
    a theoretically better grouping in exchange for staying simple and
    order-stable — a starting heuristic, tunable later if that ever
    matters in practice (per CLAUDE.md's M4 note on tunable heuristics).
    """
    claimed: set[Target] = set()
    groups: list[tuple[Target, ...]] = []
    for i, seed in enumerate(candidates):
        if seed in claimed:
            continue
        group = [seed]
        for candidate in candidates[i + 1 :]:
            if candidate in claimed:
                continue
            if co_visible_group(rig, [*group, candidate]):
                group.append(candidate)
        if len(group) >= 2:
            groups.append(tuple(group))
            claimed.update(group)
    return groups


def centroid_target(targets: Sequence[Target]) -> Target:
    """A synthetic `Target` at the mean-unit-vector centroid of
    `targets`' fixed positions.

    Used only as a sampling anchor for `constraints.best_time_tonight`
    when checking whether a group is simultaneously observable tonight
    (see `planning.py`) — never scored or shown to the user itself.
    Averaging unit vectors (rather than raw RA/Dec) handles the RA
    wraparound and pole correctly with no special-casing.
    """
    x = y = z = 0.0
    for t in targets:
        ra_rad = math.radians(t.ra_deg)
        dec_rad = math.radians(t.dec_deg)
        x += math.cos(dec_rad) * math.cos(ra_rad)
        y += math.cos(dec_rad) * math.sin(ra_rad)
        z += math.sin(dec_rad)
    n = len(targets)
    x, y, z = x / n, y / n, z / n

    dec_deg = math.degrees(math.atan2(z, math.hypot(x, y)))
    ra_deg = math.degrees(math.atan2(y, x)) % 360.0
    return Target(name="group centroid", ra_deg=ra_deg, dec_deg=dec_deg)

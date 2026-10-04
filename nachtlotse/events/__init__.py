"""Current events — comets (and later supernovae and novae) from live
sources (ROADMAP.md).

Like `weather/`, this is an optional network layer kept strictly outside
`engine/`: it only fetches and parses data (orbital elements, observed
brightness). Positions, visibility, and verdicts still come from the
engine. Every client caches on disk, falls back to an older cached copy
when the network is down (reporting its age), and raises
`EventsUnavailable` only when there's nothing at all — which callers treat
as routine, like a missing weather forecast.
"""

from __future__ import annotations

from pathlib import Path

DEFAULT_CACHE_DIR = Path(".cache/events")


class EventsUnavailable(Exception):
    """A source couldn't be fetched and nothing usable is cached."""

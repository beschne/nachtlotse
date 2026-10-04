"""Comet orbits from the Minor Planet Center — `CometEls.txt`.

One fixed-width file (~1000 comets, ~160 KB) with current osculating
elements for every known comet, refreshed by the MPC daily. Parsed into
`engine.models.CometOrbit`, keyed the way COBS names comets (see
`comet_key`), so orbits and observed brightness can be joined.

Format: https://www.minorplanetcenter.net/iau/info/CometOrbitFormat.html
("Orbital elements for software"). The H/slope magnitude columns are
deliberately not read — see `CometOrbit`'s docstring.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from nachtlotse import events
from nachtlotse.engine.models import CometOrbit
from nachtlotse.events import EventsUnavailable, _backoff, _http

COMET_ELEMENTS_URL = "https://www.minorplanetcenter.net/iau/MPCORB/CometEls.txt"
# The MPC refreshes elements daily; a day-old file is still accurate to
# well under an arcminute for ranking (see `ephemeris.comet_position`).
CACHE_TTL_HOURS = 24.0
_CACHE_FILENAME = "CometEls.txt"


@dataclass(frozen=True)
class CometOrbits:
    orbits: dict[str, CometOrbit]  # keyed by `comet_key`
    fetched_at: datetime  # when this copy was downloaded (UTC)


def comet_key(line: str) -> str:
    """The MPC's own short key for a comet line: "10P" for a numbered
    periodic comet (columns 1-5, "0010P"), else the packed provisional
    designation ("K24J030" for C/2024 J3, columns 6-12). COBS's
    `mpc_name` uses exactly these.

    A fragment of a numbered comet carries its letter in columns 11-12
    ("bt" for 73P-BT) and keys as "73P-BT" — otherwise it would share,
    and overwrite, its parent's key. Provisional designations already
    pack the fragment letter in, so they're unique as they are."""
    number, orbit_type, packed = line[0:4], line[4:5], line[5:12]
    if number.strip():
        fragment = packed.strip()
        key = f"{int(number)}{orbit_type}"
        return f"{key}-{fragment.upper()}" if fragment else key
    return packed.strip()


def parse_comet_elements(text: str) -> dict[str, CometOrbit]:
    """Every parsable line of `CometEls.txt`, keyed by `comet_key`.
    Malformed lines are skipped rather than failing the whole file."""
    orbits: dict[str, CometOrbit] = {}
    for line in text.splitlines():
        if len(line) < 103:
            continue
        try:
            orbit = CometOrbit(
                designation=line[102:158].strip(),
                perihelion_year=int(line[14:18]),
                perihelion_month=int(line[19:21]),
                perihelion_day=float(line[22:29]),
                perihelion_distance_au=float(line[30:39]),
                eccentricity=float(line[41:49]),
                argument_of_perihelion_deg=float(line[51:59]),
                longitude_of_ascending_node_deg=float(line[61:69]),
                inclination_deg=float(line[71:79]),
            )
        except ValueError:
            continue
        orbits[comet_key(line)] = orbit
    return orbits


def fetch_comet_orbits(
    *, now: datetime | None = None, cache_dir: Path | None = None
) -> CometOrbits:
    """Current comet orbits: the cached copy if it's younger than
    `CACHE_TTL_HOURS`, else a fresh download — or, if that fails, the
    cached copy whatever its age (its `fetched_at` says how old). Raises
    `EventsUnavailable` only with no network and no cache. After a failed
    download, no new attempt for `_backoff.RETRY_AFTER`.
    """
    now = now or datetime.now(UTC)
    path = (cache_dir or events.DEFAULT_CACHE_DIR) / _CACHE_FILENAME
    cached_at = _mtime(path)

    if cached_at is not None and (now - cached_at).total_seconds() < (
        CACHE_TTL_HOURS * 3600
    ):
        return CometOrbits(_read(path), cached_at)
    if _backoff.recently_failed(path, now):
        if cached_at is None:
            raise EventsUnavailable(
                "MPC comet elements: last request failed, not retrying yet"
            )
        return CometOrbits(_read(path), cached_at)
    try:
        raw = _http.get(COMET_ELEMENTS_URL, source="MPC comet elements")
    except EventsUnavailable:
        _backoff.record_failure(path)
        if cached_at is None:
            raise
        return CometOrbits(_read(path), cached_at)

    orbits = parse_comet_elements(raw.decode("utf-8", errors="replace"))
    if not orbits:
        _backoff.record_failure(path)
        raise EventsUnavailable("MPC comet elements: no parsable orbits")
    _backoff.clear_failure(path)
    _write(path, raw)
    return CometOrbits(orbits, now)


def _mtime(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    except OSError:
        return None


def _read(path: Path) -> dict[str, CometOrbit]:
    return parse_comet_elements(path.read_text(encoding="utf-8", errors="replace"))


def _write(path: Path, raw: bytes) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(".part")
        partial.write_bytes(raw)
        partial.replace(path)
    except OSError:
        pass  # best-effort — a missing cache just means a re-fetch

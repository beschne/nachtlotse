"""Supernova and nova positions and types from the IAU Transient Name
Server (TNS, wis-tns.org) — the authoritative registry every transient is
named in.

Read through TNS's public search page as CSV (`/search?...&format=csv`),
which needs no account. TNS asks users to keep such downloads to specific,
limited queries and to do anything bulk locally (see their "Getting
started" page), so this module is deliberately frugal:

- Positions are looked up per object name, only for objects another
  source (Rochester's brightness list) says are bright and current, and
  cached for good: a classified object's position and type don't change.
  A name TNS doesn't know (yet) is asked again after a day at the
  earliest. At most `MAX_LOOKUPS_PER_RUN` lookups per call, spaced out.
- Recent novae (galactic ones aren't in Rochester's supernova list) come
  from one query a day.

What TNS can't say is how bright an object is *now* — it records the
discovery magnitude (see `rochester.py`).
"""

from __future__ import annotations

import csv
import io
import json
import urllib.parse
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from nachtlotse import events
from nachtlotse.events import EventsUnavailable, _backoff, _http

SEARCH_URL = "https://www.wis-tns.org/search"
NOVA_TYPE_ID = 26  # TNS object type "Nova" (https://www.wis-tns.org/api/values)
NOVA_WINDOW_DAYS = 60
NOVA_CACHE_TTL_HOURS = 24.0
# A name TNS returned nothing for — or an object not yet classified — is
# looked up again only after this long.
RETRY_UNRESOLVED_AFTER = timedelta(hours=24)
# TNS allows anonymous search 10 requests a minute (`x-rate-limit-limit:
# 10`, observed 2026-10-04) — 8 lookups per call leaves room for the nova
# query; anything beyond waits for the next plan.
MAX_LOOKUPS_PER_RUN = 8
_OBJECTS_CACHE = "tns_objects.json"
_NOVAE_CACHE = "tns_novae.json"


@dataclass(frozen=True)
class TransientRecord:
    objname: str  # e.g. "2026aaiv"
    name: str  # with prefix, e.g. "SN 2026aaiv", "AT 2026aaom"
    ra_deg: float
    dec_deg: float
    tns_type: str  # e.g. "SN Ia", "Nova", "" when unclassified
    host: str
    discovery_mag: float | None
    discovery_date: str  # "2026-09-01 11:23:32.352" (UT), as TNS gives it

    @property
    def classified(self) -> bool:
        return self.tns_type.startswith("SN") or self.tns_type == "Nova"


def _sexagesimal_deg(text: str, *, hours: bool) -> float:
    sign = -1.0 if text.strip().startswith("-") else 1.0
    parts = [float(p) for p in text.strip().lstrip("+-").split(":")]
    value = parts[0] + parts[1] / 60.0 + parts[2] / 3600.0
    return sign * value * (15.0 if hours else 1.0)


def parse_search_csv(text: str) -> list[TransientRecord]:
    """Rows of a TNS search CSV (columns "Name", "RA", "DEC", "Obj. Type",
    "Host Name", "Discovery Mag/Flux", "Discovery Date (UT)", ...).
    Unparsable rows are skipped."""
    records = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            name = row["Name"].strip()
            discovery_mag_text = row.get("Discovery Mag/Flux", "").strip()
            records.append(
                TransientRecord(
                    objname=name.split(" ", 1)[-1],
                    name=name,
                    ra_deg=_sexagesimal_deg(row["RA"], hours=True),
                    dec_deg=_sexagesimal_deg(row["DEC"], hours=False),
                    tns_type=row.get("Obj. Type", "").strip(),
                    host=row.get("Host Name", "").strip(),
                    discovery_mag=(
                        float(discovery_mag_text) if discovery_mag_text else None
                    ),
                    discovery_date=row.get("Discovery Date (UT)", "").strip(),
                )
            )
        except (KeyError, ValueError, IndexError):
            continue
    return records


def _search(params: dict[str, str]) -> list[TransientRecord]:
    query = urllib.parse.urlencode({**params, "format": "csv"})
    raw = _http.get(f"{SEARCH_URL}?{query}", source="TNS")
    return parse_search_csv(raw.decode("utf-8", errors="replace"))


def lookup_objects(
    objnames: list[str], *, now: datetime | None = None, cache_dir: Path | None = None
) -> dict[str, TransientRecord]:
    """TNS records for `objnames` — from the permanent cache where
    possible, else one search per name (capped and spaced, see the module
    docstring). Names that couldn't be resolved are simply absent; a
    failed request stops further lookups for this run and triggers the
    usual backoff. Never raises."""
    now = now or datetime.now(UTC)
    path = (cache_dir or events.DEFAULT_CACHE_DIR) / _OBJECTS_CACHE
    cache = _read_json(path)
    records: dict[str, TransientRecord] = {}
    lookups = 0
    changed = failed = False

    for objname in objnames:
        entry = cache.get(objname)
        if entry is not None and _entry_is_final(entry, now):
            if entry["record"] is not None:
                records[objname] = TransientRecord(**entry["record"])
            continue
        if lookups >= MAX_LOOKUPS_PER_RUN or _backoff.recently_failed(path, now):
            if entry is not None and entry["record"] is not None:
                records[objname] = TransientRecord(**entry["record"])
            continue
        lookups += 1
        try:
            found = [r for r in _search({"name": objname}) if r.objname == objname]
        except EventsUnavailable as exc:
            # Recorded once; `recently_failed` then holds off the rest of
            # this run (cached records still served) and the hold-off.
            _backoff.record_failure(path, hold_off=exc.retry_after, now=now)
            failed = True
            continue
        record = found[0] if found else None
        cache[objname] = {
            "looked_up": now.isoformat(),
            "record": asdict(record) if record else None,
        }
        changed = True
        if record is not None:
            records[objname] = record

    if changed:
        if not failed:
            _backoff.clear_failure(path)
        _write_json(path, cache)
    return records


def _entry_is_final(entry: dict, now: datetime) -> bool:
    """A classified object's record never needs refreshing; an unknown
    name or a not-yet-classified object is retried after
    `RETRY_UNRESOLVED_AFTER`."""
    record = entry.get("record")
    if record is not None and TransientRecord(**record).classified:
        return True
    looked_up = datetime.fromisoformat(entry["looked_up"])
    return now - looked_up < RETRY_UNRESOLVED_AFTER


@dataclass(frozen=True)
class NovaReport:
    novae: list[TransientRecord]
    fetched_at: datetime


def fetch_recent_novae(
    *, now: datetime | None = None, cache_dir: Path | None = None
) -> NovaReport:
    """Novae discovered in the last `NOVA_WINDOW_DAYS` days — one query a
    day, same caching and backoff contract as the other sources."""
    now = now or datetime.now(UTC)
    path = (cache_dir or events.DEFAULT_CACHE_DIR) / _NOVAE_CACHE
    cached = _read_novae(path)
    if cached is not None and now - cached.fetched_at < timedelta(
        hours=NOVA_CACHE_TTL_HOURS
    ):
        return cached
    if _backoff.recently_failed(path, now):
        if cached is None:
            raise EventsUnavailable("TNS novae: last request failed, not retrying yet")
        return cached
    try:
        novae = _search(
            {
                "isTNS_AT": "yes",
                "objtype[]": str(NOVA_TYPE_ID),
                "discovered_period_value": str(NOVA_WINDOW_DAYS),
                "discovered_period_units": "days",
                "num_page": "100",
            }
        )
    except EventsUnavailable as exc:
        _backoff.record_failure(path, hold_off=exc.retry_after, now=now)
        if cached is None:
            raise
        return cached
    report = NovaReport(novae, now)
    _backoff.clear_failure(path)
    _write_json(
        path,
        {"fetched_at": now.isoformat(), "novae": [asdict(n) for n in novae]},
    )
    return report


def _read_novae(path: Path) -> NovaReport | None:
    payload = _read_json(path)
    try:
        return NovaReport(
            [TransientRecord(**n) for n in payload["novae"]],
            datetime.fromisoformat(payload["fetched_at"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _read_json(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(".part")
        partial.write_text(json.dumps(payload))
        partial.replace(path)
    except OSError:
        pass  # best-effort

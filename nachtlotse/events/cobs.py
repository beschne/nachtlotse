"""Observed comet brightness from COBS (Comet OBServation database,
cobs.si).

Why observations and not COBS's own `current_mag` field: that one is
computed from a fitted light curve and exists for nearly every comet ever
catalogued (2,393 of 2,455 in October 2026), including clearly stale
values for comets years past perihelion. Only actual recent reports say
how bright a comet is now — and which comets anyone is watching at all.

One query (`obs_list.api`, JSON, paged at 2,500) returns every report of
the last `WINDOW_DAYS` days across all comets — a few hundred typically.
Magnitudes vary with method (visual vs. CCD photometry, aperture size),
so each comet's brightness is the median of its reports, with the count
and the latest report's time alongside. Coma diameter (arcmin) is kept
the same way when observers give one.
"""

from __future__ import annotations

import json
import statistics
import urllib.parse
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from nachtlotse import events
from nachtlotse.events import EventsUnavailable, _backoff, _http

OBSERVATIONS_URL = "https://cobs.si/api/obs_list.api"
WINDOW_DAYS = 14
# Observations trickle in through the day, and a comet's brightness
# changes over days, not hours — half a day keeps COBS to two requests a
# day per machine.
CACHE_TTL_HOURS = 12.0
_CACHE_FILENAME = "cobs_brightness.json"
# Guard against a runaway paging loop if the API ever misreports `pages`.
_MAX_PAGES = 20


@dataclass(frozen=True)
class CometBrightness:
    mpc_key: str  # joins `mpc.comet_key` — "10P", "K24J030"
    designation: str  # COBS's full name, e.g. "C/2024 J3 (ATLAS)"
    magnitude: float  # median of the window's reports
    report_count: int
    last_reported: datetime  # UTC
    coma_diameter_arcmin: float | None  # median, when any report gives one


@dataclass(frozen=True)
class CometBrightnessReport:
    comets: dict[str, CometBrightness]  # keyed by `mpc_key`
    fetched_at: datetime  # UTC
    window_days: int


def summarize_observations(
    observations: list[dict[str, Any]],
) -> dict[str, CometBrightness]:
    """Per-comet medians from raw `obs_list.api` records. Reports
    without a magnitude, and fragments (`component`, e.g. 73P-B — not in
    the MPC's per-comet keying), are skipped."""
    by_comet: dict[str, list[dict[str, Any]]] = defaultdict(list)
    names: dict[str, str] = {}
    for record in observations:
        comet = record.get("comet") or {}
        key = comet.get("mpc_name")
        if not key or comet.get("component") or record.get("magnitude") is None:
            continue
        by_comet[key].append(record)
        names[key] = comet.get("fullname") or key

    summary: dict[str, CometBrightness] = {}
    for key, records in by_comet.items():
        magnitudes = [float(r["magnitude"]) for r in records]
        comas = [
            float(r["coma_diameter"])
            for r in records
            if r.get("coma_diameter") not in (None, "")
        ]
        summary[key] = CometBrightness(
            mpc_key=key,
            designation=names[key],
            magnitude=statistics.median(magnitudes),
            report_count=len(records),
            last_reported=max(_parse_time(r["obs_date"]) for r in records),
            coma_diameter_arcmin=statistics.median(comas) if comas else None,
        )
    return summary


def fetch_comet_brightness(
    *, now: datetime | None = None, cache_dir: Path | None = None
) -> CometBrightnessReport:
    """Every comet reported in the last `WINDOW_DAYS` days, with its
    median magnitude. Same caching contract as `mpc.fetch_comet_orbits`:
    fresh cache, else download, else stale cache, else
    `EventsUnavailable` — and no new attempt for `_backoff.RETRY_AFTER`
    after a failed one."""
    now = now or datetime.now(UTC)
    path = (cache_dir or events.DEFAULT_CACHE_DIR) / _CACHE_FILENAME
    cached = _read_cache(path)

    if cached is not None and (now - cached.fetched_at).total_seconds() < (
        CACHE_TTL_HOURS * 3600
    ):
        return cached
    if _backoff.recently_failed(path, now):
        if cached is None:
            raise EventsUnavailable("COBS: last request failed, not retrying yet")
        return cached
    try:
        observations = _download(now - timedelta(days=WINDOW_DAYS))
    except EventsUnavailable:
        _backoff.record_failure(path)
        if cached is None:
            raise
        return cached

    report = CometBrightnessReport(
        summarize_observations(observations), now, WINDOW_DAYS
    )
    _backoff.clear_failure(path)
    _write_cache(path, report)
    return report


def _download(since: datetime) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    page = 1
    while page <= _MAX_PAGES:
        query = urllib.parse.urlencode(
            {"from_date": f"{since:%Y-%m-%d}", "format": "json", "page": page}
        )
        raw = _http.get(f"{OBSERVATIONS_URL}?{query}", source="COBS")
        try:
            payload = json.loads(raw)
            observations.extend(payload["objects"])
            pages = int(payload["info"]["pages"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise EventsUnavailable(f"COBS response malformed: {exc}") from exc
        if page >= pages:
            return observations
        page += 1
    return observations


def _parse_time(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def _read_cache(path: Path) -> CometBrightnessReport | None:
    """A well-formed cache file, or None — corruption just means a
    re-fetch, the cache being a pure optimization."""
    try:
        payload = json.loads(path.read_text())
        comets = {
            key: CometBrightness(
                mpc_key=key,
                designation=row["designation"],
                magnitude=row["magnitude"],
                report_count=row["report_count"],
                last_reported=datetime.fromisoformat(row["last_reported"]),
                coma_diameter_arcmin=row["coma_diameter_arcmin"],
            )
            for key, row in payload["comets"].items()
        }
        return CometBrightnessReport(
            comets,
            datetime.fromisoformat(payload["fetched_at"]),
            payload["window_days"],
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def _write_cache(path: Path, report: CometBrightnessReport) -> None:
    payload = {
        "fetched_at": report.fetched_at.isoformat(),
        "window_days": report.window_days,
        "comets": {
            key: {
                "designation": c.designation,
                "magnitude": c.magnitude,
                "report_count": c.report_count,
                "last_reported": c.last_reported.isoformat(),
                "coma_diameter_arcmin": c.coma_diameter_arcmin,
            }
            for key, c in report.comets.items()
        },
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
    except OSError:
        pass  # best-effort

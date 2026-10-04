"""Current supernova (and extragalactic nova) brightness from David
Bishop's "Latest Supernovae" page (rochesterastronomy.org).

Why this and not TNS for brightness: TNS records the *discovery*
magnitude — SN 2026aaiv in NGC 7331 was found at 17.3 (ATLAS, 2026-09-01)
and peaked near 11.5 three weeks later. Rochester's page keeps a curated
table of every active supernova brighter than 17th magnitude with its
latest reported magnitude, which is exactly the "how bright is it now"
question. Positions and types still come from TNS (see `tns.py`), joined
by name.

Only one table is read: "All active supernova over mag 17.0" (columns
Name, Mag, Type, Host). A trailing "*" on a magnitude means, per the
page's own legend, "last observation is over one month old" — such
entries are kept but marked stale. Each host cell links to a sky viewer
centered on the transient itself (`...?ra=22.618227&de=34.409824...`, RA
in hours) — checked against TNS to 0.1" for 2026aaiv, 2026sqf, and
2026aaom — so the position comes along for free; only an entry without
such a link needs a TNS lookup. If the page layout changes and the
table can't be found, the source simply becomes unavailable (fail-soft),
never a wrong number.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from nachtlotse import events
from nachtlotse.events import EventsUnavailable, _backoff, _http

LATEST_SUPERNOVAE_URL = "https://www.rochesterastronomy.org/supernova.html"
# The page is large (~3 MB) and changes a few times a day at most.
CACHE_TTL_HOURS = 12.0
_CACHE_FILENAME = "rochester_brightness.json"
_TABLE_HEADING = "All active supernova over mag 17.0"


@dataclass(frozen=True)
class TransientBrightness:
    objname: str  # TNS name without prefix, e.g. "2026aaiv"
    magnitude: float
    # True for a "*" entry: last observation over a month old.
    stale: bool
    rochester_type: str  # e.g. "Ia", "II", "EGN" (extragalactic nova), "unk"
    host: str
    # The transient's own position, from the host cell's sky-viewer link;
    # None when the link is missing (then TNS has to say).
    ra_deg: float | None = None
    dec_deg: float | None = None


@dataclass(frozen=True)
class TransientBrightnessReport:
    transients: dict[str, TransientBrightness]  # keyed by objname
    fetched_at: datetime  # UTC


def tns_objname(rochester_name: str) -> str:
    """ "2026aaiv" -> "2026aaiv", "AT2026zsr" -> "2026zsr", "SN 2026x" ->
    "2026x": TNS object names carry no prefix."""
    return re.sub(r"^(SN|AT)\s*", "", rochester_name.strip(), flags=re.IGNORECASE)


def parse_latest_supernovae(page: str) -> dict[str, TransientBrightness]:
    """The "All active supernova over mag 17.0" table, keyed by TNS object
    name. Raises ValueError if the table isn't there (layout change)."""
    start = page.find(_TABLE_HEADING)
    if start < 0:
        raise ValueError(f"table {_TABLE_HEADING!r} not found")
    table_end = page.find("</table>", start)
    segment = page[start : table_end if table_end > 0 else len(page)]

    transients: dict[str, TransientBrightness] = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", segment, re.DOTALL | re.IGNORECASE):
        raw_cells = re.findall(
            r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.DOTALL | re.IGNORECASE
        )
        cells = [
            html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", cell))).strip()
            for cell in raw_cells
        ]
        if len(cells) < 4 or cells[0] == "Name":
            continue
        name, mag_text, kind, host = cells[:4]
        ra_deg, dec_deg = _linked_position(raw_cells[3])
        stale = mag_text.endswith("*")
        try:
            magnitude = float(mag_text.rstrip("*"))
        except ValueError:
            continue
        objname = tns_objname(name)
        transients[objname] = TransientBrightness(
            objname, magnitude, stale, kind, host, ra_deg, dec_deg
        )
    if not transients:
        raise ValueError(f"table {_TABLE_HEADING!r} has no parsable rows")
    return transients


def _linked_position(host_cell: str) -> tuple[float | None, float | None]:
    """(RA, Dec) in degrees from a host cell's sky-viewer link —
    `ra=<hours>&de=<degrees>` — or (None, None) without one."""
    match = re.search(
        r"[?&;]ra=(-?[0-9.]+)&(?:amp;)?de=(-?[0-9.]+)", html.unescape(host_cell)
    )
    if match is None:
        return None, None
    try:
        return float(match.group(1)) * 15.0, float(match.group(2))
    except ValueError:
        return None, None


def fetch_transient_brightness(
    *, now: datetime | None = None, cache_dir: Path | None = None
) -> TransientBrightnessReport:
    """The current table — same caching and backoff contract as
    `cobs.fetch_comet_brightness`."""
    now = now or datetime.now(UTC)
    path = (cache_dir or events.DEFAULT_CACHE_DIR) / _CACHE_FILENAME
    cached = _read_cache(path)

    if cached is not None and (now - cached.fetched_at).total_seconds() < (
        CACHE_TTL_HOURS * 3600
    ):
        return cached
    if _backoff.recently_failed(path, now):
        if cached is None:
            raise EventsUnavailable(
                "Rochester supernova list: last request failed, not retrying yet"
            )
        return cached
    try:
        raw = _http.get(LATEST_SUPERNOVAE_URL, source="Rochester supernova list")
        transients = parse_latest_supernovae(raw.decode("latin-1"))
    except (EventsUnavailable, ValueError) as exc:
        _backoff.record_failure(
            path, hold_off=getattr(exc, "retry_after", None), now=now
        )
        if cached is None:
            raise EventsUnavailable(f"Rochester supernova list: {exc}") from exc
        return cached

    report = TransientBrightnessReport(transients, now)
    _backoff.clear_failure(path)
    _write_cache(path, report)
    return report


def _read_cache(path: Path) -> TransientBrightnessReport | None:
    try:
        payload = json.loads(path.read_text())
        return TransientBrightnessReport(
            {
                key: TransientBrightness(
                    key,
                    row["magnitude"],
                    row["stale"],
                    row["rochester_type"],
                    row["host"],
                    row.get("ra_deg"),
                    row.get("dec_deg"),
                )
                for key, row in payload["transients"].items()
            },
            datetime.fromisoformat(payload["fetched_at"]),
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def _write_cache(path: Path, report: TransientBrightnessReport) -> None:
    payload = {
        "fetched_at": report.fetched_at.isoformat(),
        "transients": {
            key: {
                "magnitude": t.magnitude,
                "stale": t.stale,
                "rochester_type": t.rochester_type,
                "host": t.host,
                "ra_deg": t.ra_deg,
                "dec_deg": t.dec_deg,
            }
            for key, t in report.transients.items()
        },
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
    except OSError:
        pass  # best-effort

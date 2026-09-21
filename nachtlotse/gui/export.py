"""Text/CSV export helpers for the GUI (ROADMAP.md's "Export from the
GUI") — Shortlist/All ranked as CSV, Sites/Rigs as `.txt`.

Pure string-building only, no PySide6 import (same convention as
`data_adapter.py`, whose `ShortlistRow`/`RankedRow`/`SiteInfo`/`RigInfo`
this reuses directly rather than re-deriving from `planning`/`store`
itself) — unit-testable without the `gui` extra installed. The actual
`QFileDialog`/`QMessageBox` glue lives in each screen module, which owns
picking a destination and reporting failure; this module only builds the
text and writes it.

The sky chart's own PNG export isn't here: it reuses `chart_export.
save_shortlist_chart` (the same matplotlib path `lotse plan --chart`
uses) directly from `sky_chart.py`, not duplicated through this module.

The briefing's `.txt` export needs no builder at all — the generated
prose is already the file content — so `sky_chart.py`'s screen just
calls `write_text` with `BriefingCard.output.toPlainText()`.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

from nachtlotse.data.store import RigRecord, SiteRecord
from nachtlotse.gui import data_adapter

DEFAULT_SHORTLIST_CSV_FILENAME = "nachtlotse-shortlist.csv"
DEFAULT_RANKED_CSV_FILENAME = "nachtlotse-ranked.csv"
DEFAULT_BRIEFING_TXT_FILENAME = "nachtlotse-briefing.txt"
DEFAULT_SITES_TXT_FILENAME = "nachtlotse-sites.txt"
DEFAULT_RIGS_TXT_FILENAME = "nachtlotse-rigs.txt"

# nachtlotse/gui/export.py -> nachtlotse/ -> repo root — same `__file__`-
# anchored convention `data/store.py`'s own `_DATA_DIR` already uses,
# rather than the CLI's "wherever you happen to run it from" (`chart_
# export.DEFAULT_CHART_FILENAME` has no directory of its own): the GUI's
# cwd isn't something a user picks the way a terminal's is, especially
# launched from the Desktop `.app` bundle, so every export screen offers
# this one fixed spot as its starting point instead.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def default_export_dir() -> Path:
    """`<repo root>/exports/`, created on first use if it doesn't exist
    yet — `QFileDialog.getSaveFileName`'s starting directory for every
    export screen, and where `exports/generate_exports.py` writes its own
    output. Tracked, not gitignored: these outputs are committed alongside
    that script."""
    path = _PROJECT_ROOT / "exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


_SHORTLIST_CSV_HEADER = [
    "Target",
    "Type",
    "Alt",
    "Az",
    "Fit",
    "Reach",
    "Best",
    "Verdict",
]
_RANKED_CSV_HEADER = ["Target", "Type", "Alt", "Az", "Fit", "Reach", "Best"]


def shortlist_csv_text(rows: list[data_adapter.ShortlistRow]) -> str:
    """The Shortlist tab's own columns, as CSV — same display text the
    table cells show (e.g. "12.3°", not the raw float), so the exported
    file always matches what was on screen."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_SHORTLIST_CSV_HEADER)
    for row in rows:
        writer.writerow(
            [
                row.label,
                row.type_label,
                row.alt_text,
                row.az_text,
                row.fit_text,
                row.reach_text,
                row.best_time_text,
                row.verdict_level,
            ]
        )
    return buffer.getvalue()


def ranked_csv_text(rows: list[data_adapter.RankedRow]) -> str:
    """The All ranked tab's own columns, as CSV — see `shortlist_csv_text`."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(_RANKED_CSV_HEADER)
    for row in rows:
        writer.writerow(
            [
                row.label,
                row.type_label,
                row.alt_text,
                row.az_text,
                row.fit_text,
                row.reach_text,
                row.best_time_text,
            ]
        )
    return buffer.getvalue()


def _site_block(info: data_adapter.SiteInfo) -> str:
    """Mirrors `cli.py`'s own `_format_site_line` (`lotse sites`), off
    `SiteInfo` rather than a shared formatter — same "each UI boundary
    keeps its own small adapter" call `data_adapter.py`'s module
    docstring already makes, since `cli.py` and `gui/` are peer front
    ends (CLAUDE.md's dependency direction), not one importing the
    other."""
    title = info.name + (f"  (aka {info.aliases_text})" if info.aliases_text else "")
    lines = [
        title,
        f"    {info.coords_text}",
        f"    {info.region_text} · {info.horizon_text}",
    ]
    if info.address:
        lines.append(f"    {info.address}")
    return "\n".join(lines)


def sites_text(records: list[SiteRecord]) -> str:
    blocks = [_site_block(data_adapter.build_site_info(record)) for record in records]
    return "Nachtlotse — known sites\n\n" + "\n\n".join(blocks) + "\n"


def _rig_block(info: data_adapter.RigInfo) -> str:
    """Mirrors `cli.py`'s own `_format_rig_line` (`lotse rigs`) — see
    `_site_block`'s docstring for why this isn't shared with `cli.py`
    directly."""
    title = info.name + (f"  (aka {info.aliases_text})" if info.aliases_text else "")
    return "\n".join(
        [
            title,
            f"    {info.optics_text}",
            f"    {info.sensor_text}",
            f"    {info.fov_text}",
            f"    {info.limiting_mag_text}",
        ]
    )


def rigs_text(records: list[RigRecord]) -> str:
    blocks = [_rig_block(data_adapter.build_rig_info(record)) for record in records]
    return "Nachtlotse — known rigs\n\n" + "\n\n".join(blocks) + "\n"


def write_text(text: str, path: Path) -> None:
    """Writes `text` to `path` as UTF-8, overwriting whatever was already
    there. The one filesystem touch point every export in this module
    (and the sky chart's own PNG export) funnels through, directly or
    via `chart_export.save_shortlist_chart`."""
    path.write_text(text, encoding="utf-8")

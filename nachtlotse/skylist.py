"""SkySafari observing list (`.skylist`) export — `lotse plan --skylist`
and the GUI's Export button (ROADMAP.md's "Export to SkySafari").

Pure string-building, no I/O except `write_skylist` (same convention as
`gui/export.py`). The format was reverse-engineered from a list SkySafari
6 exported, then probed on the device with hand-edited variants:

- A block per object: `CommonName` and `CatalogNumber` lines (repeatable),
  `DefaultIndex` (0-based position), and an `ObjectID=type,0,number` that
  is SkySafari's own internal ID — not derivable from a designation.
- Catalog objects (Messier, NGC, ...) resolve by name and catalog number
  alone; the `ObjectID` can be left out, and when present, the name wins
  over a wrong ID.
- Comets resolve by name too, but only with an `ObjectID` of comet type
  (`1,0,n`) present. A placeholder number that doesn't exist in SkySafari
  works; it's only a type marker.
- Supernovae and novae aren't in SkySafari's catalogs and SkySafari 6/8
  can't create custom objects, so they're written as name-only entries.
  The list shows them greyed out and not selectable; their J2000
  coordinates go into the name, so the list still says where to point.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from nachtlotse import planning
from nachtlotse.engine.models import Target

DEFAULT_SKYLIST_FILENAME = "nachtlotse.skylist"

SkyListScope = Literal["shortlist", "ranked"]

_HEADER = "SkySafariObservingListVersion=3.0\nSortedBy=Default Order\n"

# `ObjectID` type 1 is SkySafari's comet type; the numbers below this
# base are real comets in its database. Name wins over ID (checked on the
# device), so an ID that doesn't exist only has to mark the type.
_COMET_ID_BASE = 99_990_000

_PERIODIC_COMET = re.compile(r"^(\d+[PD])/(.+)$")
_MESSIER = re.compile(r"^M(\d+)$")


@dataclass(frozen=True)
class SkyListEntry:
    """One object in the list. `object_id` is None for everything but
    comets (see the module docstring)."""

    common_names: tuple[str, ...]
    catalog_numbers: tuple[str, ...] = ()
    object_id: str | None = None


def skysafari_catalog_number(catalog_id: str) -> str:
    """The catalog's `M31` as SkySafari spells it, `M 31`; every other
    designation (`NGC 224`, `IC 1396`, ...) already matches."""
    match = _MESSIER.match(catalog_id)
    return f"M {match.group(1)}" if match else catalog_id


def catalog_entry(target: Target) -> SkyListEntry:
    """A catalog object, by name and catalog numbers (id, then aliases)."""
    numbers = [skysafari_catalog_number(target.catalog_id)] if target.catalog_id else []
    numbers += [skysafari_catalog_number(alias) for alias in target.aliases]
    return SkyListEntry(
        common_names=(target.name,) if target.name else (),
        catalog_numbers=tuple(numbers),
    )


def _comet_names(designation: str) -> tuple[str, ...]:
    """The designation as given, plus the shorter forms SkySafari lists a
    comet under: without the trailing "(Name)", and for a periodic comet
    its number ("220P") and name ("McNaught") on their own."""
    names = [designation]
    bare = designation.split(" (", 1)[0]
    if bare != designation:
        names.append(bare)
    periodic = _PERIODIC_COMET.match(bare)
    if periodic:
        names += [periodic.group(1), periodic.group(2)]
    return tuple(names)


def comet_entry(target: Target, index: int) -> SkyListEntry:
    """A comet by name, with a placeholder comet-type `ObjectID` unique
    within the list (`index` = its position among the comets)."""
    return SkyListEntry(
        common_names=_comet_names(target.name),
        object_id=f"1,0,{_COMET_ID_BASE + index}",
    )


def _ra_text(ra_deg: float) -> str:
    total_minutes = round(ra_deg / 15.0 * 60.0) % (24 * 60)
    return f"{total_minutes // 60:02d}h{total_minutes % 60:02d}m"


def _dec_text(dec_deg: float) -> str:
    total_arcmin = round(abs(dec_deg) * 60.0)
    sign = "-" if dec_deg < 0 else "+"
    return f"{sign}{total_arcmin // 60:02d}d{total_arcmin % 60:02d}m"


def transient_entry(target: Target) -> SkyListEntry:
    """A supernova or nova: name only, with J2000 coordinates appended
    (ASCII — the reference list is ASCII). SkySafari greys it out."""
    coords = f"RA {_ra_text(target.ra_deg)} Dec {_dec_text(target.dec_deg)} J2000"
    return SkyListEntry(common_names=(f"{target.name} ({coords})",))


def _targets_of(entry: planning.RankedEntry) -> tuple[Target, ...]:
    if isinstance(entry, planning.RankedGroup):
        return entry.targets
    return (entry.target,)


def entries_for_events(report: planning.EventsReport) -> list[SkyListEntry]:
    """The events observable tonight: comets first (placeholder IDs
    numbered in that order), then supernovae and novae."""
    comets = [e.target for e in report.events if e.kind == "comet"]
    entries = [comet_entry(target, i) for i, target in enumerate(comets)]
    entries += [transient_entry(e.target) for e in report.events if e.kind != "comet"]
    return entries


def entries_for_plan(
    plan: planning.NightPlan, scope: SkyListScope = "shortlist"
) -> list[SkyListEntry]:
    """The plan's catalog targets (`scope`: the shortlist, or the full
    ranking), in plan order with group members expanded, followed by the
    events observable tonight — comets, then supernovae and novae. A
    target that appears twice (e.g. a favorite also in the ranking) is
    listed once."""
    ranked = (
        [shortlisted.ranked for shortlisted in plan.shortlist]
        if scope == "shortlist"
        else plan.ranked
    )
    entries: list[SkyListEntry] = []
    seen: set[tuple[str, str]] = set()
    for item in ranked:
        for target in _targets_of(item):
            key = (target.catalog_id, target.name)
            if key not in seen:
                seen.add(key)
                entries.append(catalog_entry(target))
    if plan.events is not None:
        entries += entries_for_events(plan.events)
    return entries


def _block(index: int, entry: SkyListEntry) -> str:
    lines = ["SkyObject=BeginObject"]
    if entry.object_id is not None:
        lines.append(f"\tObjectID={entry.object_id}")
    lines += [f"\tCommonName={name}" for name in entry.common_names]
    lines += [f"\tCatalogNumber={number}" for number in entry.catalog_numbers]
    lines += [f"\tDefaultIndex={index}", "EndObject=SkyObject"]
    return "\n".join(lines) + "\n"


def skylist_text(entries: Iterable[SkyListEntry]) -> str:
    return _HEADER + "".join(_block(i, entry) for i, entry in enumerate(entries))


def write_skylist(entries: Iterable[SkyListEntry], path: Path) -> None:
    path.write_text(skylist_text(entries), encoding="utf-8")

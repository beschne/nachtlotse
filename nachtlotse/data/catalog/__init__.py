"""Deep-sky catalog — data, not engine logic.

Split into `mag_*.yaml` files by apparent magnitude rather than by source
catalog (Messier/NGC/IC): the file a target lives in is decided purely by
brightness, so a site+rig's computed limiting magnitude will eventually be
able to load only the files it actually needs. New magnitude bins are
picked up automatically — this module globs `mag_*.yaml` in its own
directory rather than importing each one by name — but loaded in
brightest-first order (`_brightness_sort_key`), not filename order:
`planning.rank_targets`'s `limit` caps evaluation to the first N entries
of `CATALOG`, so the load order is what makes "evaluate only 50" mean
"evaluate the 50 brightest" rather than an arbitrary alphabetical slice.

`mag_unknown.yaml` is the one exception to "split by magnitude": it holds
objects with no reliably sourced integrated magnitude at all (see
SKIPPED-OBJECTS.md) rather than a numeric range. Admission for these
still requires a real, citable `catalog_id` and a real `size_arcmin` —
brightness isn't knowable, but visibility and framing still are, and
those are what the engine actually ranks on.

Each physical object gets exactly one `Target` entry, in whichever file its
brightest commonly-used designation belongs to; other catalog numbers for
the same object (e.g. M31's NGC 224) go in `aliases`, not a second entry —
otherwise the same object would show up twice in a ranking. This matters a
lot for Messier vs. NGC, since most Messier objects also have an NGC
number.

Coordinates are J2000 equinox, accurate to roughly an arcminute — good
enough for altitude ranking, not for plate-solving/pointing. `size_arcmin`
and `magnitude` are approximate published values from standard references,
good for framing/visibility heuristics, not precision use. Kept
deliberately small and curated (not the full ~7840-entry NGC or
~5386-entry IC catalogs) — see CLAUDE.md's own M0 note on a "small core
catalog". `catalog_id` isn't limited to Messier/NGC/IC — any catalog with
a real, citable designation (Sharpless, Abell, van den Bergh, …) is fair
game as long as the object has legitimate coordinates and size, and either
a legitimate magnitude or a documented reason it has none.

Every entry also carries `types` — one or more of `Target.TargetType`
(emission/reflection/planetary/dark nebula, galaxy, galaxy group, open/
globular cluster, variable star) — so targets can be filtered by
category. An object can be more than one at once (M42 is both an
emission and a reflection nebula).

Favorites (ROADMAP.md's "Favorites in the catalog" — a target that always
shows regardless of ranking) are deliberately NOT recorded in these files:
this catalog is shared, curated reference data meant to be identical for
every clone of the repo, and one person's "always show me T CrB" is not a
sourced fact about the object the way its coordinates or magnitude are.
Instead, favorites live the same way sites/rigs do (see `data/store.py`'s
own docstring) — a local, gitignored `favorites_local.yaml` next to this
package, one `catalog_id` per line, loaded by `_load_local_favorite_
catalog_ids` and folded into the matching `Target.favorite` at load time
below. `favorites_local.template.yaml` (committed) documents the format
with one real example, T CrB — copy it to get started.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from nachtlotse.engine.models import Target

_CATALOG_DIR = Path(__file__).resolve().parent

_BIN_FILENAME_RE = re.compile(
    r"^mag_(?:lt_(?P<lt>\d+)|(?P<low>\d+)_\d+|unknown)\.yaml$"
)


def _brightness_sort_key(path: Path) -> float:
    """Lower is brighter/evaluated-first — see `planning.rank_targets`'s
    `limit`, which relies on catalog order being brightest-first so that
    capping evaluation to the first N objects still surfaces the most
    attractive targets rather than an alphabetically-arbitrary slice.

    `mag_lt_6.yaml` sorts before every numeric bin (no lower bound to key
    on); `mag_unknown.yaml` sorts after all of them, magnitude being
    exactly what's not known about those entries.
    """
    match = _BIN_FILENAME_RE.match(path.name)
    if match is None:
        raise ValueError(
            f"catalog bin file doesn't match the mag_*.yaml pattern: {path.name}"
        )
    if match["lt"] is not None:
        return -float(match["lt"])
    if match["low"] is not None:
        return float(match["low"])
    return float("inf")  # mag_unknown.yaml


def _target_from_dict(raw: dict[str, Any]) -> Target:
    size = raw.get("size_arcmin")
    magnitude = raw.get("magnitude")
    return Target(
        name=raw["name"],
        ra_deg=float(raw["ra_deg"]),
        dec_deg=float(raw["dec_deg"]),
        catalog_id=raw.get("catalog_id", ""),
        aliases=tuple(raw.get("aliases", [])),
        size_arcmin=(float(size[0]), float(size[1])) if size else (0.0, 0.0),
        magnitude=float(magnitude) if magnitude is not None else None,
        types=tuple(raw.get("types", [])),
        # NOT read from `raw` — see module docstring: favorites live in
        # favorites_local.yaml, folded in by _load_catalog below, never in
        # this shared catalog data itself.
    )


def _load_local_favorite_catalog_ids() -> set[str]:
    """The user's own starred `catalog_id`s, from the gitignored
    `favorites_local.yaml` next to this package — empty if that file
    doesn't exist yet (same optional-file convention `store.py`'s own
    `prose_local.yaml` uses: no favorites configured is a normal, common
    state, not an error). Resolved from `_CATALOG_DIR` rather than a
    fixed module-level path so tests that monkeypatch `_CATALOG_DIR` to
    an isolated tmp_path stay isolated for this too."""
    path = _CATALOG_DIR.parent / "favorites_local.yaml"
    if not path.exists():
        return set()
    return set(yaml.safe_load(path.read_text(encoding="utf-8")) or [])


def _load_catalog() -> list[Target]:
    favorite_ids = _load_local_favorite_catalog_ids()
    targets: list[Target] = []
    for path in sorted(_CATALOG_DIR.glob("mag_*.yaml"), key=_brightness_sort_key):
        raw_targets = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for raw in raw_targets:
            target = _target_from_dict(raw)
            if target.catalog_id in favorite_ids:
                target = replace(target, favorite=True)
            targets.append(target)
    return targets


CATALOG: list[Target] = _load_catalog()

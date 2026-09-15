"""Deep-sky catalog — data, not engine logic.

Split into `mag_*.yaml` files by apparent magnitude rather than by source
catalog (Messier/NGC/IC): the file a target lives in is decided purely by
brightness, so a site+rig's computed limiting magnitude will eventually be
able to load only the files it actually needs. New magnitude bins are
picked up automatically — this module globs `mag_*.yaml` in its own
directory rather than importing each one by name.

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
globular cluster) — so targets can be filtered by category. An object can
be more than one at once (M42 is both an emission and a reflection
nebula).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nachtlotse.engine.models import Target

_CATALOG_DIR = Path(__file__).resolve().parent


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
    )


def _load_catalog() -> list[Target]:
    targets: list[Target] = []
    for path in sorted(_CATALOG_DIR.glob("mag_*.yaml")):
        raw_targets = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        targets.extend(_target_from_dict(raw) for raw in raw_targets)
    return targets


CATALOG: list[Target] = _load_catalog()

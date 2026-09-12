"""Persistence for known observing sites.

No location data ships in code — this repo is meant to be cloned by anyone,
anywhere, and hardcoded sites for one specific region would just be dead
weight (or worse, something every new user has to notice and delete) for
everyone else. Instead, sites live entirely in a local, gitignored
`sites_local.yaml` next to this file, loaded at import time by
`_load_local_sites`. `sites_local.template.yaml` (committed, never read by
this module) documents the format with two real examples — copy it to
`sites_local.yaml` and edit to get started; see `require_sites`.

Horizon profiles: `horizon_points` gives measured (azimuth, altitude) pairs
directly. `sector` is a shorthand for sites that only document a
visible-azimuth arc (no point-by-point survey yet) — [start_deg, end_deg]
(clockwise, wrapping past 360° if start > end), optionally with a minimum
altitude for the open arc as a third element (default 0°); everything
outside that arc becomes a 90° wall via `_sector_to_points`. Neither key
means an unrestricted 360° view.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from nachtlotse.engine.models import HorizonProfile, Site


@dataclass(frozen=True)
class SiteRecord:
    """A site plus descriptive metadata the pure engine model doesn't need."""

    site: Site
    region: str
    bortle: str
    address: str = ""
    aliases: tuple[str, ...] = ()


def _sector_to_points(
    start_deg: float, end_deg: float, min_alt_deg: float = 0.0
) -> list[tuple[float, float]]:
    """Synthesize a top-hat HorizonProfile from a visible-azimuth sector.

    `start_deg` -> `end_deg` is read clockwise (wrapping past 360° if
    `start_deg > end_deg`). Open inside the sector at `min_alt_deg`, walled
    off (90°) outside it.
    """
    if (start_deg, end_deg) == (0.0, 360.0) and min_alt_deg == 0.0:
        return []
    epsilon = 0.01
    return [
        (start_deg % 360.0, min_alt_deg),
        ((start_deg - epsilon) % 360.0, 90.0),
        (end_deg % 360.0, min_alt_deg),
        ((end_deg + epsilon) % 360.0, 90.0),
    ]


def _site_record_from_dict(raw: dict[str, Any]) -> SiteRecord:
    if "horizon_points" in raw:
        points = [(float(az), float(alt)) for az, alt in raw["horizon_points"]]
    elif "sector" in raw:
        start_deg, end_deg, *rest = raw["sector"]
        min_alt_deg = float(rest[0]) if rest else 0.0
        points = _sector_to_points(float(start_deg), float(end_deg), min_alt_deg)
    else:
        points = []

    return SiteRecord(
        site=Site(
            name=raw["name"],
            lat_deg=float(raw["lat_deg"]),
            lon_deg=float(raw["lon_deg"]),
            elevation_m=float(raw["elevation_m"]),
            tz=raw.get("tz", "Europe/Berlin"),
            horizon=HorizonProfile(points=points),
        ),
        region=raw.get("region", ""),
        bortle=raw.get("bortle", ""),
        address=raw.get("address", ""),
        aliases=tuple(raw.get("aliases", [])),
    )


def _parse_sites_yaml(path: Path) -> list[SiteRecord]:
    if not path.exists():
        return []
    raw_sites = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [_site_record_from_dict(raw) for raw in raw_sites]


_DATA_DIR = Path(__file__).resolve().parent
_LOCAL_SITES_PATH = _DATA_DIR / "sites_local.yaml"
_TEMPLATE_SITES_PATH = _DATA_DIR / "sites_local.template.yaml"


def _load_local_sites() -> list[SiteRecord]:
    """Load the user's local site list — empty if it doesn't exist yet."""
    return _parse_sites_yaml(_LOCAL_SITES_PATH)


SITES: list[SiteRecord] = _load_local_sites()


def require_sites() -> None:
    """Raise a clear, actionable error if no sites are configured yet."""
    if not SITES:
        raise ValueError(
            "No observing sites configured. Copy "
            f"nachtlotse/data/{_TEMPLATE_SITES_PATH.name} to "
            f"nachtlotse/data/{_LOCAL_SITES_PATH.name} and add your own "
            "sites — that file documents the format with two examples."
        )


def load_sites() -> list[Site]:
    return [record.site for record in SITES]


def list_site_names() -> list[str]:
    return [record.site.name for record in SITES]


def get_site_record(name: str) -> SiteRecord:
    """Look up a site by exact name/alias, falling back to a unique
    case-insensitive substring match against the name.
    """
    require_sites()
    needle = name.strip().casefold()
    for record in SITES:
        if record.site.name.casefold() == needle:
            return record
        if any(alias.casefold() == needle for alias in record.aliases):
            return record

    substring_matches = [
        record for record in SITES if needle in record.site.name.casefold()
    ]
    if len(substring_matches) == 1:
        return substring_matches[0]
    if len(substring_matches) > 1:
        ambiguous = ", ".join(record.site.name for record in substring_matches)
        raise ValueError(f"Ambiguous site {name!r}. Matches: {ambiguous}")

    known = ", ".join(list_site_names())
    raise ValueError(f"Unknown site {name!r}. Known sites: {known}")


def default_site_record() -> SiteRecord:
    """The first configured site — i.e. whatever the user listed first in
    their local site file.
    """
    require_sites()
    return SITES[0]

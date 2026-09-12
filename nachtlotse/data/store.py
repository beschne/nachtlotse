"""Persistence for known observing sites and rigs.

No location or equipment data ships in code — this repo is meant to be
cloned by anyone, anywhere, with any gear, and hardcoding one person's
setup would just be dead weight (or worse, something every new user has to
notice and delete) for everyone else. Instead, both sites and rigs live
entirely in local, gitignored `sites_local.yaml` / `rigs_local.yaml` files
next to this one, loaded at import time. `sites_local.template.yaml` /
`rigs_local.template.yaml` (committed, never read by this module) document
the formats with real examples — copy one to get started; see
`require_sites` / `require_rigs`.

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

from nachtlotse.engine.models import HorizonProfile, Mount, Optics, Rig, Sensor, Site


@dataclass(frozen=True)
class SiteRecord:
    """A site plus descriptive metadata the pure engine model doesn't need."""

    site: Site
    region: str
    bortle: str
    address: str = ""
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class RigRecord:
    """A rig plus aliases the pure engine model doesn't need."""

    rig: Rig
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


def _rig_record_from_dict(raw: dict[str, Any]) -> RigRecord:
    optics_raw = raw["optics"]
    sensor_raw = raw["sensor"]
    mount_raw = raw["mount"]

    zenith_avoid_deg = mount_raw.get("zenith_avoid_deg")

    return RigRecord(
        rig=Rig(
            name=raw["name"],
            optics=Optics(
                name=optics_raw.get("name", raw["name"]),
                focal_length_mm=float(optics_raw["focal_length_mm"]),
                aperture_mm=float(optics_raw["aperture_mm"]),
            ),
            sensor=Sensor(
                name=sensor_raw.get("name", ""),
                width_px=int(sensor_raw["width_px"]),
                height_px=int(sensor_raw["height_px"]),
                pixel_um=float(sensor_raw["pixel_um"]),
            ),
            mount=Mount(
                name=mount_raw.get("name", raw["name"]),
                kind=mount_raw["kind"],
                zenith_avoid_deg=(
                    float(zenith_avoid_deg) if zenith_avoid_deg is not None else None
                ),
            ),
        ),
        aliases=tuple(raw.get("aliases", [])),
    )


def _parse_yaml_records(path: Path, from_dict: Any) -> list[Any]:
    if not path.exists():
        return []
    raw_records = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [from_dict(raw) for raw in raw_records]


def _parse_sites_yaml(path: Path) -> list[SiteRecord]:
    return _parse_yaml_records(path, _site_record_from_dict)


def _parse_rigs_yaml(path: Path) -> list[RigRecord]:
    return _parse_yaml_records(path, _rig_record_from_dict)


_DATA_DIR = Path(__file__).resolve().parent
_LOCAL_SITES_PATH = _DATA_DIR / "sites_local.yaml"
_TEMPLATE_SITES_PATH = _DATA_DIR / "sites_local.template.yaml"
_LOCAL_RIGS_PATH = _DATA_DIR / "rigs_local.yaml"
_TEMPLATE_RIGS_PATH = _DATA_DIR / "rigs_local.template.yaml"


def _load_local_sites() -> list[SiteRecord]:
    """Load the user's local site list — empty if it doesn't exist yet."""
    return _parse_sites_yaml(_LOCAL_SITES_PATH)


def _load_local_rigs() -> list[RigRecord]:
    """Load the user's local rig list — empty if it doesn't exist yet."""
    return _parse_rigs_yaml(_LOCAL_RIGS_PATH)


SITES: list[SiteRecord] = _load_local_sites()
RIGS: list[RigRecord] = _load_local_rigs()


def require_sites() -> None:
    """Raise a clear, actionable error if no sites are configured yet."""
    if not SITES:
        raise ValueError(
            "No observing sites configured. Copy "
            f"nachtlotse/data/{_TEMPLATE_SITES_PATH.name} to "
            f"nachtlotse/data/{_LOCAL_SITES_PATH.name} and add your own "
            "sites — that file documents the format with two examples."
        )


def require_rigs() -> None:
    """Raise a clear, actionable error if no rigs are configured yet."""
    if not RIGS:
        raise ValueError(
            "No rigs configured. Copy "
            f"nachtlotse/data/{_TEMPLATE_RIGS_PATH.name} to "
            f"nachtlotse/data/{_LOCAL_RIGS_PATH.name} and add your own "
            "rigs — that file documents the format with four examples."
        )


def load_sites() -> list[Site]:
    return [record.site for record in SITES]


def list_site_names() -> list[str]:
    return [record.site.name for record in SITES]


def list_rig_names() -> list[str]:
    return [record.rig.name for record in RIGS]


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


def get_rig_record(name: str) -> RigRecord:
    """Look up a rig by exact name/alias, falling back to a unique
    case-insensitive substring match against the name.
    """
    require_rigs()
    needle = name.strip().casefold()
    for record in RIGS:
        if record.rig.name.casefold() == needle:
            return record
        if any(alias.casefold() == needle for alias in record.aliases):
            return record

    substring_matches = [
        record for record in RIGS if needle in record.rig.name.casefold()
    ]
    if len(substring_matches) == 1:
        return substring_matches[0]
    if len(substring_matches) > 1:
        ambiguous = ", ".join(record.rig.name for record in substring_matches)
        raise ValueError(f"Ambiguous rig {name!r}. Matches: {ambiguous}")

    known = ", ".join(list_rig_names())
    raise ValueError(f"Unknown rig {name!r}. Known rigs: {known}")


def default_site_record() -> SiteRecord:
    """The first configured site — i.e. whatever the user listed first in
    their local site file.
    """
    require_sites()
    return SITES[0]


def default_rig_record() -> RigRecord:
    """The first configured rig — i.e. whatever the user listed first in
    their local rig file.
    """
    require_rigs()
    return RIGS[0]

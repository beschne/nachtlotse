"""Pure data models of the engine core.

No dependency on UI, network, or persistence — see CLAUDE.md, section
"Architecture".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import pairwise
from typing import Literal


@dataclass(frozen=True)
class HorizonProfile:
    """Minimum altitude above the horizon, depending on azimuth.

    `points` are (azimuth 0..360, N=0, clockwise) -> minimum altitude in
    degrees. Linearly interpolated between control points; the last and
    first points close the circle (wrap-around at 360°/0°).
    """

    points: list[tuple[float, float]]

    def min_alt(self, az_deg: float) -> float:
        if not self.points:
            return 0.0
        pts = sorted(self.points, key=lambda p: p[0])
        az = az_deg % 360.0

        for (az_a, alt_a), (az_b, alt_b) in pairwise(pts):
            if az_a <= az <= az_b:
                return _lerp(az, az_a, alt_a, az_b, alt_b)

        # Wrap-around between the last and first control point.
        az_a, alt_a = pts[-1]
        az_b, alt_b = pts[0]
        span = (az_b - az_a) % 360.0
        offset = (az - az_a) % 360.0
        if span == 0.0:
            return alt_a
        return _lerp(offset, 0.0, alt_a, span, alt_b)


def _lerp(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    if x1 == x0:
        return y0
    fraction = (x - x0) / (x1 - x0)
    return y0 + fraction * (y1 - y0)


@dataclass(frozen=True)
class Site:
    name: str
    lat_deg: float
    lon_deg: float
    elevation_m: float
    tz: str  # IANA timezone, e.g. "Europe/Berlin"
    horizon: HorizonProfile
    # Sky-darkness inputs for engine.framing's surface-brightness reach
    # factor. Both optional and independent of each other; None means
    # "not documented", not a worst-case guess — same convention as
    # Target.magnitude/size_arcmin. When both are given,
    # framing.sky_brightness_mag_arcsec2 prefers the real measurement over
    # the Bortle-derived estimate.
    bortle_class: float | None = None  # e.g. 4.5, parsed from "4-5"/"4–5"
    # Measured zenith sky brightness at new moon (SQM reading).
    zenith_sky_brightness_mag_arcsec2: float | None = None


@dataclass(frozen=True)
class Optics:
    name: str
    focal_length_mm: float
    aperture_mm: float


@dataclass(frozen=True)
class Sensor:
    name: str
    width_px: int
    height_px: int
    pixel_um: float


@dataclass(frozen=True)
class Mount:
    name: str
    kind: Literal["altaz", "eq"]
    zenith_avoid_deg: float | None = None


@dataclass(frozen=True)
class Rig:
    name: str
    optics: Optics
    sensor: Sensor
    mount: Mount

    @property
    def sampling_arcsec_px(self) -> float:
        """Plate scale: arcseconds per pixel."""
        return 206.265 * self.sensor.pixel_um / self.optics.focal_length_mm

    @property
    def fov_deg(self) -> tuple[float, float]:
        """Field of view (width, height) in degrees."""
        width_mm = self.sensor.width_px * self.sensor.pixel_um / 1000.0
        height_mm = self.sensor.height_px * self.sensor.pixel_um / 1000.0
        fov_width_deg = math.degrees(
            2 * math.atan(width_mm / (2 * self.optics.focal_length_mm))
        )
        fov_height_deg = math.degrees(
            2 * math.atan(height_mm / (2 * self.optics.focal_length_mm))
        )
        return fov_width_deg, fov_height_deg


# A target can carry more than one — e.g. M42 is both an emission and a
# reflection nebula, and a Local Group member is both a galaxy and (if
# catalogued as part of one) a galaxy_group.
TargetType = Literal[
    "emission_nebula",
    "reflection_nebula",
    "planetary_nebula",
    "dark_nebula",
    "galaxy",
    "galaxy_group",
    "open_cluster",
    "globular_cluster",
]

# Human-readable labels for TargetType, shared by every front end so
# "emission nebula" isn't spelled out differently in one place vs. another.
TARGET_TYPE_LABELS: dict[TargetType, str] = {
    "emission_nebula": "Emission Nebula",
    "reflection_nebula": "Reflection Nebula",
    "planetary_nebula": "Planetary Nebula",
    "dark_nebula": "Dark Nebula",
    "galaxy": "Galaxy",
    "galaxy_group": "Galaxy Group",
    "open_cluster": "Open Cluster",
    "globular_cluster": "Globular Cluster",
}


@dataclass(frozen=True)
class Target:
    """A catalog target with a fixed position (J2000 equinox)."""

    name: str
    ra_deg: float
    dec_deg: float
    catalog_id: str = ""
    # Alternate catalog designations for the same physical object (e.g. M31
    # -> ("NGC 224",)) — lets a target appear once, findable under any of
    # its names, instead of duplicated across catalog files.
    aliases: tuple[str, ...] = ()
    # Apparent (major, minor) axis, arcminutes. (0.0, 0.0) means "unknown" —
    # framing scoring treats that as unconstrained, not "infinitely small".
    size_arcmin: tuple[float, float] = (0.0, 0.0)
    # Apparent visual magnitude — for variable objects, the brighter
    # (numerically lower) of its known extremes. None means no reliably
    # sourced integrated magnitude exists for this object at all (true for
    # most diffuse emission/dark nebulae and Abell planetary nebulae — see
    # SKIPPED-OBJECTS.md) — treated as unconstrained by anything that
    # filters/ranks on brightness, the same convention as size_arcmin ==
    # (0.0, 0.0) for unknown size. Never a stand-in for "very faint".
    magnitude: float | None = None
    # What kind of object this is, for filtering/search — see TargetType.
    # Empty only for a target not yet classified; every catalog entry is
    # expected to carry at least one (enforced by a catalog test).
    types: tuple[TargetType, ...] = ()


@dataclass(frozen=True)
class WeatherSummary:
    """The engine's view of a weather forecast, aggregated over an
    observing window — independent of whichever provider supplied it (see
    `weather/open_meteo.py`). Optional input to `engine.scoring`; the
    engine core never fetches this itself.
    """

    max_cloud_cover_pct: float
    avg_cloud_cover_pct: float
    max_wind_kmh: float
    min_dew_point_spread_c: float  # smallest (temperature - dew point); low = dew risk


@dataclass(frozen=True)
class Verdict:
    level: Literal["GO", "MARGINAL", "SKIP"]
    reasons: list[str]  # every number comes from the engine
    # one Verdict per shortlisted target, not one per night — see roadmap

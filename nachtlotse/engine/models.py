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


@dataclass(frozen=True)
class Target:
    """A catalog target with a fixed position (J2000 equinox)."""

    name: str
    ra_deg: float
    dec_deg: float
    catalog_id: str = ""


@dataclass(frozen=True)
class Verdict:
    level: Literal["GO", "MARGINAL", "SKIP"]
    reasons: list[str]

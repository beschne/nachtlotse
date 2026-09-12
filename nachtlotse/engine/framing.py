"""Framing and alt-az field-rotation heuristics.

Framing: does the target's angular size fit the rig's field of view? Purely
geometric, independent of time — see `framing_score`.

Field rotation: an alt-az mount tracks in altitude/azimuth, not parallel to
the sky's own rotation, so the frame itself slowly rotates relative to the
stars over an imaging session. That rotation rate is the time-derivative of
the parallactic angle (astroplan computes the angle itself) and diverges as
a target's path passes near the zenith. Numerically calibrated for this
project's latitude range (~50°N): roughly 0.3–0.5°/min far from the zenith,
climbing past ~1.5°/min inside a ~5° zenith radius and past ~20°/min inside
1°. Eq mounts don't have this problem at all — `has_safe_field_rotation`
always returns True for them, regardless of zenith proximity.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from astropy.time import Time

from nachtlotse.engine.constraints import build_fixed_target, build_observer
from nachtlotse.engine.models import Rig, Site, Target

# Symmetric baseline for the finite-difference rotation-rate estimate.
# Differencing right at a near-zenith transit is numerically degenerate
# (azimuth itself is undefined exactly at the pole), so this deliberately
# looks a few minutes either side rather than differentiating at a point —
# calibrated against the transit region, see the module docstring.
_ROTATION_RATE_BASELINE = timedelta(minutes=5)

# ~5° zenith-avoidance radius at this project's latitudes (see calibration
# above) — a starting heuristic, not a precision limit; tune per rig/mount
# if needed.
DEFAULT_MAX_ROTATION_RATE_DEG_PER_MIN = 1.5

_MIN_FILL_FRACTION = 0.2


def framing_score(rig: Rig, target: Target) -> float:
    """How well the target's angular size fits the rig's field of view.

    1.0: the target's major axis fills at least 20% of the FoV's shorter
    dimension without being clipped. Scales down toward 0.0 as the target
    is either lost in a tiny fraction of the frame (fill < 20%) or badly
    clipped (overflows it). Targets with no known size (`size_arcmin ==
    (0, 0)`) score 1.0 — treated as framing-unconstrained, not
    "infinitely small".
    """
    major_arcmin, _minor_arcmin = target.size_arcmin
    if major_arcmin <= 0.0:
        return 1.0

    fov_width_deg, fov_height_deg = rig.fov_deg
    fov_short_arcmin = min(fov_width_deg, fov_height_deg) * 60.0
    if fov_short_arcmin <= 0.0:
        return 0.0

    fill_fraction = major_arcmin / fov_short_arcmin

    if fill_fraction > 1.0:
        return max(0.0, 1.0 - (fill_fraction - 1.0))
    if fill_fraction >= _MIN_FILL_FRACTION:
        return 1.0
    return fill_fraction / _MIN_FILL_FRACTION


def field_rotation_rate_deg_per_min(
    site: Site, target: Target, when: datetime
) -> float:
    """Rate of change of the parallactic angle (deg/min) at `when`, over a
    symmetric 5-minute baseline — the quantity that diverges as a target
    passes near the zenith.
    """
    observer = build_observer(site)
    fixed_target = build_fixed_target(target)
    half = _ROTATION_RATE_BASELINE / 2

    q_before = observer.parallactic_angle(Time(when - half), fixed_target).deg
    q_after = observer.parallactic_angle(Time(when + half), fixed_target).deg

    delta_deg = ((q_after - q_before + 180.0) % 360.0) - 180.0
    return abs(delta_deg) / (_ROTATION_RATE_BASELINE.total_seconds() / 60.0)


def has_safe_field_rotation(
    rig: Rig,
    site: Site,
    target: Target,
    when: datetime,
    *,
    max_rate_deg_per_min: float = DEFAULT_MAX_ROTATION_RATE_DEG_PER_MIN,
) -> bool:
    """Whether `rig` can track `target` at `site`/`when` without excessive
    field rotation. Alt-az mounts only — always True for eq mounts, which
    don't have this problem regardless of zenith proximity.
    """
    if rig.mount.kind != "altaz":
        return True
    return bool(
        field_rotation_rate_deg_per_min(site, target, when) <= max_rate_deg_per_min
    )

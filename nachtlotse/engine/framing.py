"""Framing, alt-az field-rotation, and limiting-magnitude heuristics.

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

Limiting magnitude: how faint a target a rig can usefully image at a given
sky darkness — see `photographic_limiting_magnitude`. Meant to eventually
bound which catalog magnitude bins (see `data/catalog/`) are worth loading
for a given site+rig, instead of curating "interesting" NGC/IC objects by
hand.

Sky brightness: `sky_brightness_mag_arcsec2` resolves a site's zenith,
new-moon sky darkness — a real SQM measurement if the site has one,
otherwise a Bortle-class estimate, otherwise `None` (unconstrained). Feeds
the not-yet-built surface-brightness `reach` factor in `target_priority_score`
(see CLAUDE.md's Roadmap): extended objects rank on light per pixel, not
integrated magnitude, which favors a small bright planetary nebula over a
large faint one at the same total brightness.
"""

from __future__ import annotations

import math
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


_MAX_ALTITUDE_DEG = 90.0


def target_priority_score(alt_deg: float, fit: float) -> float:
    """Ranks targets by altitude *and* framing fit together, so a target
    that barely fits the frame doesn't win purely for sitting high in the
    sky — see `framing_score`.

    Multiplicative rather than a weighted sum: fit acts as a veto (a fit
    near 0.0 crushes the score regardless of altitude) instead of needing
    its own tunable weight next to altitude. Among targets that already
    fit comfortably (`fit == 1.0`), this reduces to plain altitude —
    today's ranking is unchanged for the common case.
    """
    return (alt_deg / _MAX_ALTITUDE_DEG) * fit


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


# Naked-eye limiting magnitude (NELM) by Bortle dark-sky class — commonly
# cited approximate midpoints for John Bortle's 2001 scale. Linearly
# interpolated for fractional classes (a site documented as "4-5" -> 4.5).
_NELM_BY_BORTLE: dict[float, float] = {
    1.0: 7.8,
    2.0: 7.3,
    3.0: 6.8,
    4.0: 6.3,
    5.0: 5.8,
    6.0: 5.25,
    7.0: 4.75,
    8.0: 4.0,
    9.0: 3.5,
}

# The sky darkness the aperture-only formula below implicitly assumes
# (roughly Bortle 3-4) — subtracting this calibrates it to any other class.
_NELM_FORMULA_REFERENCE = 6.9

# Rough gain a stacked astrophotography session has over naked-eye visual
# limiting magnitude, for a "typical" session (tens of minutes of total
# integration). By far the biggest source of uncertainty in this estimate —
# a much longer or shorter session shifts the real number substantially.
# Tune this against your own results, not the physics below.
DEFAULT_INTEGRATION_GAIN_MAG = 7.0


def _interpolate_by_bortle_class(table: dict[float, float], bortle_class: float) -> float:
    """Linear interpolation over a Bortle-class-keyed table (a site
    documented as "4-5" -> 4.5), clamped to the standard scale's 1-9
    range."""
    lower = min(max(math.floor(bortle_class), 1), 9)
    upper = min(max(math.ceil(bortle_class), 1), 9)
    if lower == upper:
        return table[float(lower)]
    fraction = bortle_class - lower
    return table[float(lower)] + fraction * (table[float(upper)] - table[float(lower)])


def _naked_eye_limiting_magnitude(bortle_class: float) -> float:
    """NELM at a (possibly fractional) Bortle class, via linear
    interpolation between the standard scale's integer classes."""
    return _interpolate_by_bortle_class(_NELM_BY_BORTLE, bortle_class)


# Zenith sky brightness (mag/arcsec², SQM-equivalent) by Bortle dark-sky
# class — commonly cited approximate midpoints for John Bortle's 2001
# scale, the SQM-reading counterpart to _NELM_BY_BORTLE above. A starting
# heuristic, not a calibrated instrument reading — see
# sky_brightness_mag_arcsec2(), which prefers a real measurement when a
# site has one.
_SKY_BRIGHTNESS_BY_BORTLE: dict[float, float] = {
    1.0: 21.85,
    2.0: 21.7,
    3.0: 21.5,
    4.0: 21.0,
    5.0: 19.75,
    6.0: 18.5,
    7.0: 18.0,
    8.0: 17.5,
    9.0: 17.0,
}


def sky_brightness_mag_arcsec2(site: Site) -> float | None:
    """Zenith, new-moon sky brightness for `site`, mag/arcsec² (SQM scale).

    A real measurement (`site.zenith_sky_brightness_mag_arcsec2`) always
    wins; otherwise estimated from `site.bortle_class`; `None` if neither
    is documented — unconstrained, not a worst-case guess, the same
    convention as `Target.magnitude`/`size_arcmin`. Doesn't correct for
    the target's actual altitude or tonight's moon phase — a real
    measurement is zenith-at-new-moon by definition, and the estimate
    inherits the same reference point; that correction is a separate,
    not-yet-built refinement (see CLAUDE.md's Roadmap).
    """
    if site.zenith_sky_brightness_mag_arcsec2 is not None:
        return site.zenith_sky_brightness_mag_arcsec2
    if site.bortle_class is not None:
        return _interpolate_by_bortle_class(_SKY_BRIGHTNESS_BY_BORTLE, site.bortle_class)
    return None


def photographic_limiting_magnitude(
    aperture_mm: float,
    bortle_class: float,
    *,
    integration_gain_mag: float = DEFAULT_INTEGRATION_GAIN_MAG,
) -> float:
    """Rough estimate of the faintest magnitude a stacked astrophotography
    session can usefully reach, for a given aperture and sky darkness.

    Deliberately simple — a real exposure-time calculator would also need
    sensor QE, read noise, pixel scale, and actual integration time, none
    of which this project tracks yet. Built from the classic visual
    telescope limiting-magnitude formula (2.7 + 5*log10(D_mm)), adjusted
    for the site's actual sky darkness and a single tunable constant for
    the photographic gain over visual. A starting heuristic for bounding
    the catalog by brightness, not a precision prediction — CLAUDE.md's M4
    note on tunable heuristics applies here just as much.
    """
    visual_dark_sky_mag = 2.7 + 5 * math.log10(aperture_mm)
    sky_adjustment_mag = (
        _naked_eye_limiting_magnitude(bortle_class) - _NELM_FORMULA_REFERENCE
    )
    return visual_dark_sky_mag + integration_gain_mag + sky_adjustment_mag

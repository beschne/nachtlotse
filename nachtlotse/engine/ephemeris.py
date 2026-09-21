"""Altitude, azimuth, and transit time of a target — deterministic via skyfield.

Pure engine: no UI, network, or file I/O except for the one-time load of the
JPL ephemeris (de421) at module import. The ephemeris is kept in a local
cache directory, not in the git repo (see .gitignore).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from skyfield import almanac
from skyfield.api import Loader, Star, wgs84
from skyfield.timelib import Time

from nachtlotse.engine.models import Site, Target

_CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache" / "skyfield"
_load = Loader(str(_CACHE_DIR))
_timescale = _load.timescale()
_ephemeris = _load("de421.bsp")
_earth = _ephemeris["earth"]
_moon = _ephemeris["moon"]


@dataclass(frozen=True)
class AltAz:
    """Topocentric position of a target at a point in time."""

    alt_deg: float
    az_deg: float
    distance_au: float


def _topos(site: Site) -> object:
    return wgs84.latlon(site.lat_deg, site.lon_deg, elevation_m=site.elevation_m)


def _star(target: Target) -> Star:
    return Star(ra_hours=target.ra_deg / 15.0, dec_degrees=target.dec_deg)


def _time(when: datetime) -> Time:
    if when.tzinfo is None:
        raise ValueError("when must be timezone-aware (aware datetime)")
    return _timescale.from_datetime(when)


def altaz(site: Site, target: Target, when: datetime) -> AltAz:
    """Altitude/azimuth of a target at a site at a point in time."""
    observer = _earth + _topos(site)
    t = _time(when)
    apparent = observer.at(t).observe(_star(target)).apparent()
    alt, az, distance = apparent.altaz()
    return AltAz(alt_deg=alt.degrees, az_deg=az.degrees, distance_au=distance.au)


def altitude_series(
    site: Site, target: Target, start: datetime, end: datetime, num_samples: int = 49
) -> list[tuple[datetime, AltAz]]:
    """Altitude/azimuth at `num_samples` evenly spaced points across
    [start, end] — an altitude curve for plotting, not a constraint check.
    """
    observer = _earth + _topos(site)
    times = _timescale.tt_jd(np.linspace(_time(start).tt, _time(end).tt, num_samples))
    apparent = observer.at(times).observe(_star(target)).apparent()
    alt, az, distance = apparent.altaz()
    sample_datetimes = times.utc_datetime()

    return [
        (
            sample_datetimes[i],
            AltAz(
                alt_deg=alt.degrees[i], az_deg=az.degrees[i], distance_au=distance.au[i]
            ),
        )
        for i in range(num_samples)
    ]


def moon_altaz_series(
    site: Site, start: datetime, end: datetime, num_samples: int = 49
) -> list[tuple[datetime, AltAz]]:
    """Altitude/azimuth of the Moon at `num_samples` evenly spaced points
    across [start, end] — mirrors `altitude_series`, but observes the
    Moon body directly (real orbital motion) instead of treating it as a
    fixed `Star` the way every catalog target is."""
    observer = _earth + _topos(site)
    times = _timescale.tt_jd(np.linspace(_time(start).tt, _time(end).tt, num_samples))
    apparent = observer.at(times).observe(_moon).apparent()
    alt, az, distance = apparent.altaz()
    sample_datetimes = times.utc_datetime()

    return [
        (
            sample_datetimes[i],
            AltAz(
                alt_deg=alt.degrees[i], az_deg=az.degrees[i], distance_au=distance.au[i]
            ),
        )
        for i in range(num_samples)
    ]


def moon_rise_set_events(
    site: Site, start: datetime, end: datetime
) -> list[tuple[datetime, bool]]:
    """Moonrise (True) / moonset (False) events within [start, end],
    time-ordered. Empty if the Moon doesn't cross the horizon in this
    window at all — up the whole time, or down the whole time; check
    `moon_altaz_series`'s altitude to tell those two cases apart."""
    f = almanac.risings_and_settings(_ephemeris, _moon, _topos(site))
    times, events = almanac.find_discrete(_time(start), _time(end), f)
    return [(t.utc_datetime(), bool(e)) for t, e in zip(times, events)]


def moon_phase_angle_deg(when: datetime) -> float:
    """The Moon's real phase angle at `when`, 0-360°: 0° new, 180° full
    (`skyfield.almanac.moon_phase` — the geocentric ecliptic-longitude
    difference between Moon and Sun). Unlike a bare illumination
    fraction, this also carries waxing (0-180°) vs. waning (180-360°),
    so a phase icon can show the correct crescent/gibbous shape, not
    just how much of the disk is lit."""
    return almanac.moon_phase(_ephemeris, _time(when)).degrees


def find_transit(
    site: Site, target: Target, start: datetime, end: datetime
) -> datetime:
    """Time of upper culmination (max. altitude) within the window [start, end).

    Raises ValueError if no culmination falls within the window (e.g.
    because the window is shorter than a sidereal day and poorly aligned).
    """
    topos = _topos(site)
    f = almanac.meridian_transits(_ephemeris, _star(target), topos)
    t0 = _time(start)
    t1 = _time(end)
    times, events = almanac.find_discrete(t0, t1, f)

    # event == 1 marks the upper culmination (meridian transit),
    # event == 0 the lower one (antimeridian).
    transits = times[events == 1]
    if len(transits) == 0:
        raise ValueError(
            f"No culmination of {target.name!r} within window {start} .. {end}"
        )
    return transits[0].utc_datetime()


def max_altitude(
    site: Site, target: Target, start: datetime, end: datetime
) -> tuple[datetime, AltAz]:
    """Time and position of the highest altitude within [start, end].

    Altitude has a single maximum (the meridian transit) per sidereal day
    and is monotonic on either side of it. If the transit falls inside the
    window, that's the maximum; otherwise the window is monotonic
    throughout, so the maximum sits at one of its two edges.
    """
    try:
        transit_time = find_transit(site, target, start, end)
    except ValueError:
        start_pos = altaz(site, target, start)
        end_pos = altaz(site, target, end)
        if start_pos.alt_deg >= end_pos.alt_deg:
            return start, start_pos
        return end, end_pos
    return transit_time, altaz(site, target, transit_time)

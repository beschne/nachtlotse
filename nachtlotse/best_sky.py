""""Where's the best sky?" — cross-site weather comparison.

A different question from `planning.plan_night`: not "what should I shoot
at my usual site tonight", but "which of my configured sites has the
clearest night, within an optional radius of a reference site". Purely an
orchestration of `data.store` (site list, coordinates) and `weather`
(forecast) — no new engine constraint or scoring rule, per the roadmap
note in CLAUDE.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from nachtlotse.engine import constraints
from nachtlotse.engine.models import Site, WeatherSummary
from nachtlotse.weather import open_meteo

_EARTH_RADIUS_KM = 6371.0


def _distance_km(site_a: Site, site_b: Site) -> float:
    """Great-circle distance between two sites (haversine)."""
    lat1, lon1, lat2, lon2 = (
        math.radians(site_a.lat_deg),
        math.radians(site_a.lon_deg),
        math.radians(site_b.lat_deg),
        math.radians(site_b.lon_deg),
    )
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    )
    return 2.0 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _bearing_deg(origin: Site, destination: Site) -> float:
    """Initial compass bearing (0=N, 90=E, ...) from `origin` to `destination`."""
    lat1, lat2 = math.radians(origin.lat_deg), math.radians(destination.lat_deg)
    dlon = math.radians(destination.lon_deg - origin.lon_deg)
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(
        dlon
    )
    return math.degrees(math.atan2(x, y)) % 360.0


@dataclass(frozen=True)
class SiteSkyReport:
    """One site's weather for its own dark window on the planned night."""

    site: Site
    distance_km: float
    bearing_deg: float | None  # from the reference site; None if distance is ~0
    weather: WeatherSummary | None


def compare_sites(
    reference: Site,
    candidates: list[Site],
    when: datetime,
    max_distance_km: float | None = None,
) -> list[SiteSkyReport]:
    """Weather comparison across `candidates` on the night of `when`.

    Each site is judged in its own astronomical-twilight dark window (not
    a shared clock time — sites can differ in latitude/timezone). Ranked
    by max cloud cover in that window, clearest first, same criterion
    `engine.scoring.verdict_for_target` already uses to gate GO/MARGINAL/
    SKIP; a site whose weather is unreachable sorts last, not first —
    "unknown" is not "clear".

    `max_distance_km`, if given, drops any candidate farther than that
    from `reference` (haversine great-circle distance); None keeps every
    candidate, including sites at any distance from `reference`.
    """
    reports = []
    for site in candidates:
        distance_km = _distance_km(reference, site)
        if max_distance_km is not None and distance_km > max_distance_km:
            continue
        bearing_deg = _bearing_deg(reference, site) if distance_km > 0.01 else None

        evening_start, morning_end = constraints.dark_window(site, when)
        try:
            hours = open_meteo.fetch_hourly_cached(site.lat_deg, site.lon_deg)
        except open_meteo.WeatherUnavailable:
            weather = None
        else:
            weather = open_meteo.summarize_window(hours, evening_start, morning_end)

        reports.append(
            SiteSkyReport(
                site=site,
                distance_km=distance_km,
                bearing_deg=bearing_deg,
                weather=weather,
            )
        )

    def sort_key(report: SiteSkyReport) -> tuple[int, float]:
        if report.weather is None:
            return (1, 0.0)
        return (0, report.weather.max_cloud_cover_pct)

    reports.sort(key=sort_key)
    return reports

"""GO/MARGINAL/SKIP verdict heuristic (M4).

Pure and deterministic given its inputs — weather is optional (pass
`None` when unavailable) and the verdict still comes out, just without
cloud/wind/dew-point reasons; the target ranking upstream of this already
works fully offline (see `engine.constraints`/`engine.framing`).

The thresholds below are a deliberate starting heuristic, not physics —
CLAUDE.md's M4 note calls this out explicitly: the weighting of clouds vs.
moon vs. altitude vs. rotation is subjective and meant to be tuned over
time. Grouped here, named, and commented so that tuning is a one-line
change, not an archaeology exercise.
"""

from __future__ import annotations

from typing import Literal

from nachtlotse.engine.models import Verdict, WeatherSummary

_Level = Literal["GO", "MARGINAL", "SKIP"]

# Cloud cover (%) forecast across the target's imaging window.
SKIP_CLOUD_COVER_PCT = 80.0
MARGINAL_CLOUD_COVER_PCT = 40.0

# Wind (km/h) — mainly a concern for lightweight/exposed rigs (tracking
# error, vibration blur), less so for a squat smart telescope.
SKIP_WIND_KMH = 40.0
MARGINAL_WIND_KMH = 25.0

# Dew point spread (°C): temperature minus dew point. Below this, dew/frost
# on the optics becomes a real risk over a multi-hour session.
MARGINAL_DEW_POINT_SPREAD_C = 2.0

# Altitude (deg) of a target's best moment tonight. Below this,
# atmospheric extinction and seeing degrade the shot even under a clear
# sky — a "clear but low" night is MARGINAL, not GO.
MARGINAL_ALTITUDE_DEG = 40.0

_LEVEL_ORDER = {"GO": 0, "MARGINAL": 1, "SKIP": 2}


def verdict_for_target(
    alt_deg: float, *, weather: WeatherSummary | None = None
) -> Verdict:
    """GO/MARGINAL/SKIP for a target at its best altitude tonight.

    `alt_deg` is the altitude already computed by the engine ranking (see
    `engine.constraints.best_time_tonight`) — this function only combines
    it with weather, it doesn't recompute sky geometry. Called once per
    shortlisted target (see `planning.plan_night`), not once for the night
    as a whole — two targets in the same shortlist can land on different
    verdicts if their altitudes differ.
    """
    level: _Level = "GO"
    reasons: list[str] = []

    def downgrade(new_level: _Level, reason: str) -> None:
        nonlocal level
        if _LEVEL_ORDER[new_level] > _LEVEL_ORDER[level]:
            level = new_level
        reasons.append(reason)

    if weather is None:
        # Without a forecast there's no way to rule out cloud cover, wind,
        # or dew — GO would claim a certainty we don't have, so this caps
        # at MARGINAL rather than falling through to sky geometry alone.
        downgrade(
            "MARGINAL", "no weather forecast available — cannot confirm clear skies"
        )
    else:
        if weather.max_cloud_cover_pct >= SKIP_CLOUD_COVER_PCT:
            downgrade("SKIP", f"cloud cover up to {weather.max_cloud_cover_pct:.0f}%")
        elif weather.max_cloud_cover_pct >= MARGINAL_CLOUD_COVER_PCT:
            downgrade(
                "MARGINAL", f"cloud cover up to {weather.max_cloud_cover_pct:.0f}%"
            )

        if weather.max_wind_kmh >= SKIP_WIND_KMH:
            downgrade("SKIP", f"wind up to {weather.max_wind_kmh:.0f} km/h")
        elif weather.max_wind_kmh >= MARGINAL_WIND_KMH:
            downgrade("MARGINAL", f"wind up to {weather.max_wind_kmh:.0f} km/h")

        if weather.min_dew_point_spread_c <= MARGINAL_DEW_POINT_SPREAD_C:
            downgrade(
                "MARGINAL",
                f"dew risk (only {weather.min_dew_point_spread_c:.1f}°C above dew point)",
            )

    if alt_deg < MARGINAL_ALTITUDE_DEG:
        downgrade("MARGINAL", f"target only reaches {alt_deg:.0f}° altitude")

    if not reasons:
        reasons.append(
            f"clear sky forecast and {alt_deg:.0f}° altitude — good conditions"
        )

    return Verdict(level=level, reasons=reasons)

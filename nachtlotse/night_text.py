"""The night verdict as text — `lotse plan`'s and the GUI's header line
(ROADMAP.md's "Night verdict"). Shared by both front ends the way
`frame_export.summary_lines` shares the framing preview's text; the
numbers all come from `engine.night`, only the local clock times are
formatted here, at the UI boundary.
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

from nachtlotse.engine import night
from nachtlotse.engine.models import NightVerdict


def verdict_line(verdict: NightVerdict, local_tz: ZoneInfo) -> str:
    """One line answering "is it worth setting up tonight?" — e.g.
    "Night verdict: GO — clear 21:30–03:10 (5.7 h)"."""
    prefix = "Night verdict: "
    if verdict.level is None:
        if verdict.forecast_h <= 0.0:
            return prefix + "unknown — no weather forecast for this night"
        return (
            prefix + f"unknown — the forecast covers only {verdict.forecast_h:.1f} "
            f"of the {verdict.window_h:.1f} h dark window"
        )
    run = verdict.longest_run
    if run is None:
        return (
            prefix + f"{verdict.level} — no clear stretch, cloud cover of "
            f"{night.CLEAR_CLOUD_COVER_PCT:.0f}% or more throughout"
        )
    start = run.start.astimezone(local_tz)
    end = run.end.astimezone(local_tz)
    if verdict.level == "GO":
        return prefix + f"GO — clear {start:%H:%M}–{end:%H:%M} ({run.duration_h:.1f} h)"
    return (
        prefix + f"{verdict.level} — longest clear run {run.duration_h:.1f} h "
        f"from {start:%H:%M}, GO needs {night.GO_CLEAR_RUN_H:g} h"
    )


def held_back_line(verdict: NightVerdict) -> str | None:
    """What cost the night time, costliest first — None when nothing did."""
    if not verdict.held_back_by:
        return None
    return "Held back by: " + "; ".join(item.detail for item in verdict.held_back_by)

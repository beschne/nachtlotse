"""Night verdict: is tonight worth setting up for at all?

Answers the question before "what do I shoot?" — judged on the longest
unbroken clear stretch inside the dark window, not on the window's
average (an average of 40% cloud can mean "clear until 01:00, then
closed"). The per-target GO/MARGINAL/SKIP (`engine.scoring`) stays as it
is; this frames it.

Pure and deterministic: hourly forecast values and the Moon's numbers go
in, a `NightVerdict` comes out. No fetching, no time zones — the front
ends turn the run's start/end into local times.

Thresholds are a starting heuristic, named here so tuning is a one-line
change, like those in `engine.scoring`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from typing import Literal

from nachtlotse.engine.models import (
    ClearRun,
    HeldBack,
    HourlyConditions,
    NightVerdict,
)
from nachtlotse.engine.scoring import (
    MARGINAL_CLOUD_COVER_PCT,
    MARGINAL_DEW_POINT_SPREAD_C,
    MARGINAL_WIND_KMH,
)

_Level = Literal["GO", "MARGINAL", "SKIP"]

# An hour counts as clear below this cloud cover — the same line
# `engine.scoring` draws between GO and MARGINAL for a target.
CLEAR_CLOUD_COVER_PCT = MARGINAL_CLOUD_COVER_PCT

# Longest clear run (hours): at least this for GO, below the second value
# SKIP, MARGINAL in between.
GO_CLEAR_RUN_H = 3.0
SKIP_CLEAR_RUN_H = 1.5

# The Moon is only named as a cost when it's at least this illuminated (%).
MOON_NOTE_ILLUMINATION_PCT = 50.0

# Weight of high cloud (cirrus) against low and mid cloud — see
# `effective_cloud_cover_pct`.
HIGH_CLOUD_WEIGHT = 0.5

_HOUR = timedelta(hours=1)
# Forecast coverage shorter than the window by less than this is full.
_COVERAGE_TOLERANCE_H = 1.0 / 60.0


def effective_cloud_cover_pct(
    total_pct: float,
    low_pct: float | None,
    mid_pct: float | None,
    high_pct: float | None,
) -> float:
    """Cloud cover as it matters for imaging: thin high cloud counts at
    half weight, the denser low and mid layers in full — the largest of
    `low`, `mid` and half of `high`, never above the `total`. The layers
    overlap, so this can't see low and mid cloud covering different parts
    of the sky and so errs on the clear side there. Without all three
    layers, the total stands."""
    if low_pct is None or mid_pct is None or high_pct is None:
        return total_pct
    return min(total_pct, max(low_pct, mid_pct, HIGH_CLOUD_WEIGHT * high_pct))


def cloud_at(hours: Sequence[HourlyConditions], when: datetime) -> float | None:
    """The cloud cover of the forecast hour containing `when`, or None
    when the forecast doesn't cover that moment."""
    for hour in hours:
        if hour.when <= when < hour.when + _HOUR:
            return hour.cloud_cover_pct
    return None


def _hours_in_window(
    hours: Sequence[HourlyConditions], start: datetime, end: datetime
) -> list[tuple[HourlyConditions, datetime, datetime]]:
    """Each forecast hour's overlap with [start, end], in time order;
    hours that don't overlap it are dropped."""
    overlaps = []
    for hour in sorted(hours, key=lambda h: h.when):
        begin, finish = max(hour.when, start), min(hour.when + _HOUR, end)
        if finish > begin:
            overlaps.append((hour, begin, finish))
    return overlaps


def clear_runs(
    hours: Sequence[HourlyConditions],
    window_start: datetime,
    window_end: datetime,
    max_cloud_pct: float = CLEAR_CLOUD_COVER_PCT,
) -> list[ClearRun]:
    """Unbroken stretches of forecast hours below `max_cloud_pct` inside
    the window, clipped to it, in time order. Time the forecast doesn't
    cover is never counted as clear."""
    runs: list[ClearRun] = []
    for hour, begin, finish in _hours_in_window(hours, window_start, window_end):
        if hour.cloud_cover_pct >= max_cloud_pct:
            continue
        if runs and runs[-1].end == begin:
            runs[-1] = ClearRun(runs[-1].start, finish)
        else:
            runs.append(ClearRun(begin, finish))
    return runs


def _level(longest_h: float) -> _Level:
    if longest_h >= GO_CLEAR_RUN_H:
        return "GO"
    if longest_h >= SKIP_CLEAR_RUN_H:
        return "MARGINAL"
    return "SKIP"


def night_verdict(
    hours: Sequence[HourlyConditions],
    window_start: datetime,
    window_end: datetime,
    *,
    moon_illumination_pct: float,
    moon_up_h: float,
) -> NightVerdict:
    """The night's verdict from the hourly forecast over the dark window
    `[window_start, window_end]`.

    `moon_up_h` is how long the Moon is above the horizon inside the
    window. A SKIP needs the forecast to cover the whole window: if part
    of it is unknown, a short clear run there can't rule the rest out, so
    the level stays None; GO and MARGINAL still stand, since the covered
    part already shows that much clear time.
    """
    window_h = (window_end - window_start).total_seconds() / 3600.0
    covered = _hours_in_window(hours, window_start, window_end)
    forecast_h = sum((finish - begin).total_seconds() for _, begin, finish in covered)
    forecast_h /= 3600.0

    runs = clear_runs(hours, window_start, window_end)
    longest = max(runs, key=lambda run: run.duration_h, default=None)
    clear_h = sum(run.duration_h for run in runs)

    level: _Level | None
    if not covered:
        level = None
    else:
        level = _level(longest.duration_h if longest else 0.0)
        if level == "SKIP" and forecast_h < window_h - _COVERAGE_TOLERANCE_H:
            level = None

    def hours_where(condition: Callable[[HourlyConditions], bool]) -> float:
        return (
            sum(
                (finish - begin).total_seconds()
                for hour, begin, finish in covered
                if condition(hour)
            )
            / 3600.0
        )

    held_back = [
        HeldBack(
            "cloud",
            hours_where(lambda h: h.cloud_cover_pct >= CLEAR_CLOUD_COVER_PCT),
            f"cloud cover of {CLEAR_CLOUD_COVER_PCT:.0f}% or more for {{h:.1f}} h",
        ),
        HeldBack(
            "wind",
            hours_where(lambda h: h.wind_kmh >= MARGINAL_WIND_KMH),
            f"wind of {MARGINAL_WIND_KMH:.0f} km/h or more for {{h:.1f}} h",
        ),
        HeldBack(
            "dew",
            hours_where(lambda h: h.dew_point_spread_c <= MARGINAL_DEW_POINT_SPREAD_C),
            f"dew point within {MARGINAL_DEW_POINT_SPREAD_C:.0f}°C of the air "
            "temperature for {h:.1f} h",
        ),
    ]
    if moon_illumination_pct >= MOON_NOTE_ILLUMINATION_PCT:
        held_back.append(
            HeldBack(
                "moon",
                moon_up_h,
                f"Moon {moon_illumination_pct:.0f}% illuminated, up for {{h:.1f}} h",
            )
        )
    costly = tuple(
        HeldBack(item.term, item.duration_h, item.detail.format(h=item.duration_h))
        for item in sorted(held_back, key=lambda item: -item.duration_h)
        if item.duration_h > 0.0
    )

    return NightVerdict(
        level=level,
        window_h=window_h,
        forecast_h=forecast_h,
        clear_h=clear_h,
        longest_run=longest,
        held_back_by=costly,
    )

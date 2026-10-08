"""Tests for the night verdict's text (nachtlotse/night_text.py)."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from nachtlotse import night_text, planning
from nachtlotse.engine.models import ClearRun, HeldBack, NightVerdict

BERLIN = ZoneInfo("Europe/Berlin")


def _verdict(level, run=None, forecast_h=8.0, held_back=()) -> NightVerdict:
    return NightVerdict(
        level=level,
        window_h=8.0,
        forecast_h=forecast_h,
        clear_h=run.duration_h if run else 0.0,
        longest_run=run,
        held_back_by=tuple(held_back),
    )


def test_go_line_names_the_clear_run_in_local_time() -> None:
    # 19:30-01:10 UTC is 21:30-03:10 CEST (5 h 40 min).
    run = ClearRun(
        datetime(2026, 10, 8, 19, 30, tzinfo=UTC),
        datetime(2026, 10, 9, 1, 10, tzinfo=UTC),
    )
    assert (
        night_text.verdict_line(_verdict("GO", run), BERLIN)
        == "Night verdict: GO — clear 21:30–03:10 (5.7 h)"
    )


def test_skip_line_says_what_the_rule_needs() -> None:
    run = ClearRun(
        datetime(2026, 10, 8, 20, 0, tzinfo=UTC),
        datetime(2026, 10, 8, 21, 0, tzinfo=UTC),
    )
    assert (
        night_text.verdict_line(_verdict("SKIP", run), BERLIN)
        == "Night verdict: SKIP — longest clear run 1.0 h from 22:00, GO needs 3 h"
    )


def test_a_night_without_any_clear_stretch() -> None:
    assert (
        night_text.verdict_line(_verdict("SKIP"), BERLIN)
        == "Night verdict: SKIP — no clear stretch, cloud cover of 40% or more "
        "throughout"
    )


def test_unknown_lines_distinguish_no_forecast_from_partial() -> None:
    assert night_text.verdict_line(_verdict(None, forecast_h=0.0), BERLIN) == (
        "Night verdict: unknown — no weather forecast for this night"
    )
    assert night_text.verdict_line(_verdict(None, forecast_h=3.0), BERLIN) == (
        "Night verdict: unknown — the forecast covers only 3.0 of the 8.0 h dark window"
    )


def test_held_back_line_lists_details_or_nothing() -> None:
    assert night_text.held_back_line(_verdict("GO")) is None
    items = [
        HeldBack("wind", 4.0, "wind of 25 km/h or more for 4.0 h"),
        HeldBack("moon", 3.5, "Moon 98% illuminated, up for 3.5 h"),
    ]
    assert night_text.held_back_line(_verdict("GO", held_back=items)) == (
        "Held back by: wind of 25 km/h or more for 4.0 h; "
        "Moon 98% illuminated, up for 3.5 h"
    )


def test_plan_night_carries_a_night_verdict(template_sites, template_rigs) -> None:
    from nachtlotse.data import store

    site = store.default_site_record().site
    rig = store.default_rig_record().rig
    plan = planning.plan_night(site, rig, datetime.now(UTC), limit=5)
    assert plan.night_verdict is not None
    assert plan.night_verdict.level == "GO"  # conftest forecast: clear all night
    assert 0.0 < plan.night_verdict.window_h <= 24.0

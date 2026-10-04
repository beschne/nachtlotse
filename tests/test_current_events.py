"""Current events in planning (ROADMAP.md) — sources mocked, the engine
real: positions, observability, limits, and verdicts are all computed.

Orbit lines are verbatim from the MPC's CometEls.txt of 2026-10-04; the
COBS medians mirror that day's real reports.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from nachtlotse import planning
from nachtlotse.engine import framing
from nachtlotse.engine.models import HorizonProfile, Mount, Optics, Rig, Sensor, Site
from nachtlotse.events import EventsUnavailable, cobs, mpc

COMET_ELS = (
    "    CK24J030  2026 11 25.4268  3.865524  0.999946   74.0905  285.9594   75.6391  20261003   8.6  4.0  C/2024 J3 (ATLAS)                                        MPC xxxxx\n"
    "    CK26A020  2026 12 22.3526  1.937795  0.997667  155.9372  206.5878   82.3059  20261003  11.3  4.0  C/2026 A2 (Bok)                                          MPC xxxxx\n"
    "0010P         2026 08  2.1040  1.417739  0.537442  195.4604  117.7968   12.0271  20261003  13.1  4.0  10P/Tempel                                               MPC xxxxx\n"
    "0161P         2026 11 27.1779  1.265114  0.836178   47.0647    1.4736   95.7918  20261003   8.5  6.0  161P/Hartley-IRAS                                        MPEC 2026-T05\n"
)

FETCHED_AT = datetime(2026, 10, 4, 9, 0, tzinfo=UTC)
WHEN = datetime(2026, 10, 4, 10, 0, tzinfo=UTC)

SITE = Site(
    name="Bad Homburg",
    lat_deg=50.2266,
    lon_deg=8.6180,
    elevation_m=190.0,
    tz="Europe/Berlin",
    horizon=HorizonProfile(points=[]),
    bortle_class=5.0,
)

# ZWO Seestar S30 Pro: 160 mm, f/5.3 (30 mm), 3840x2160 px at 2.9 um, alt-az.
SEESTAR = Rig(
    name="Seestar S30 Pro",
    optics=Optics(name="S30 Pro", focal_length_mm=160.0, aperture_mm=30.0),
    sensor=Sensor(name="IMX585", width_px=3840, height_px=2160, pixel_um=2.9),
    mount=Mount(name="Seestar", kind="altaz"),
)


def _seen(key, name, magnitude, coma=None, reports=10):
    return cobs.CometBrightness(
        mpc_key=key,
        designation=name,
        magnitude=magnitude,
        report_count=reports,
        last_reported=datetime(2026, 10, 3, 21, 0, tzinfo=UTC),
        coma_diameter_arcmin=coma,
    )


BRIGHTNESS = {
    "161P": _seen("161P", "161P/Hartley-IRAS", 11.4, 3.4, reports=47),
    "K26A020": _seen("K26A020", "C/2026 A2 (Bok)", 13.9, 1.05),
    "10P": _seen("10P", "10P/Tempel", 9.8, 6.0),  # dec -33: too low at 50N
    "K24J030": _seen("K24J030", "C/2024 J3 (ATLAS)", 14.1, 1.15),  # just too faint
    "95P": _seen("95P", "95P/Chiron", 18.5),  # filed as an asteroid, no comet orbit
}


@pytest.fixture
def live_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        mpc,
        "fetch_comet_orbits",
        lambda: mpc.CometOrbits(mpc.parse_comet_elements(COMET_ELS), FETCHED_AT),
    )
    monkeypatch.setattr(
        cobs,
        "fetch_comet_brightness",
        lambda: cobs.CometBrightnessReport(dict(BRIGHTNESS), FETCHED_AT, 14),
    )


def test_event_limiting_magnitude_applies_a_margin_per_kind() -> None:
    limit = framing.photographic_limiting_magnitude(30.0, 5.0)
    assert framing.event_limiting_magnitude(SEESTAR, SITE, "comet") == pytest.approx(
        limit - 2.0
    )
    assert framing.event_limiting_magnitude(
        SEESTAR, SITE, "supernova"
    ) == pytest.approx(limit - 1.0)
    unknown_sky = replace(SITE, bortle_class=None)
    assert framing.event_limiting_magnitude(SEESTAR, unknown_sky, "comet") is None


def test_current_events_ranks_observable_comets_bright_enough(live_sources) -> None:
    report = planning.current_events(SITE, SEESTAR, WHEN)

    assert [e.target.name for e in report.events] == [
        "C/2026 A2 (Bok)",  # ~67° high at nightfall
        "161P/Hartley-IRAS",  # ~37°
    ]
    hartley = report.events[1]
    assert hartley.kind == "comet"
    assert hartley.target.types == ("comet",)
    assert hartley.target.magnitude == 11.4
    assert hartley.target.size_arcmin == (3.4, 3.4)  # COBS coma diameter
    assert hartley.magnitude_source == "COBS: median of 47 reports, latest 2026-10-03"
    assert 0.0 < hartley.motion_deg_per_hour < 1.0
    start, end = planning.constraints.dark_window(SITE, WHEN)
    assert start <= hartley.best_time <= end
    assert hartley.pos.alt_deg >= planning.constraints.DEFAULT_MIN_ALT_DEG


def test_current_events_explains_every_comet_it_leaves_out(live_sources) -> None:
    report = planning.current_events(SITE, SEESTAR, WHEN)
    reasons = {s.name: s.reason for s in report.skipped}

    assert "not observable tonight" in reasons["10P/Tempel"]
    assert "too faint" in reasons["C/2024 J3 (ATLAS)"]
    assert "limit 14.0" in reasons["C/2024 J3 (ATLAS)"]
    assert "no MPC comet orbit" in reasons["95P/Chiron"]
    assert [s.magnitude for s in report.skipped] == sorted(
        s.magnitude for s in report.skipped
    )


def test_current_events_has_no_limit_without_a_bortle_class(live_sources) -> None:
    report = planning.current_events(replace(SITE, bortle_class=None), SEESTAR, WHEN)
    assert "C/2024 J3 (ATLAS)" in {e.target.name for e in report.events}


def test_current_events_names_its_sources(live_sources) -> None:
    notes = planning.current_events(SITE, SEESTAR, WHEN).notes
    assert any("MPC" in n and "2026-10-04 09:00" in n for n in notes)
    assert any("COBS" in n and "14 days" in n for n in notes)


def test_current_events_verdicts_follow_weather_and_darkness(live_sources) -> None:
    report = planning.current_events(SITE, SEESTAR, WHEN, darkness="nautical")
    for event in report.events:
        assert event.verdict.level == "MARGINAL"
        assert any("no astronomical darkness" in r for r in event.verdict.reasons)


def test_current_events_is_empty_but_explained_when_offline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def offline():
        raise EventsUnavailable("MPC comet elements request failed: offline")

    monkeypatch.setattr(mpc, "fetch_comet_orbits", offline)
    report = planning.current_events(SITE, SEESTAR, WHEN)
    assert report.events == [] and report.skipped == []
    assert report.notes == [
        "Comets unavailable: MPC comet elements request failed: offline"
    ]


def test_plan_night_gathers_events_only_when_asked(live_sources) -> None:
    assert planning.plan_night(SITE, SEESTAR, WHEN, limit=5).events is None
    plan = planning.plan_night(SITE, SEESTAR, WHEN, limit=5, include_events=True)
    assert plan.events is not None
    assert {e.target.name for e in plan.events.events} == {
        "C/2026 A2 (Bok)",
        "161P/Hartley-IRAS",
    }


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("161P/Hartley-IRAS", "161P/Hartley-IRAS"),
        ("161P", "161P/Hartley-IRAS"),
        ("161p", "161P/Hartley-IRAS"),
        ("C/2026 A2 (Bok)", "C/2026 A2 (Bok)"),
        ("C/2026 A2", "C/2026 A2 (Bok)"),
        ("c/2026a2", "C/2026 A2 (Bok)"),
    ],
)
def test_find_event_accepts_the_usual_ways_to_name_a_comet(
    live_sources, query, expected
) -> None:
    report = planning.current_events(SITE, SEESTAR, WHEN)
    event = planning.find_event(report, query)
    assert isinstance(event, planning.RankedEvent)
    assert event.target.name == expected


def test_find_event_returns_skipped_events_and_none(live_sources) -> None:
    report = planning.current_events(SITE, SEESTAR, WHEN)
    skipped = planning.find_event(report, "10P")
    assert isinstance(skipped, planning.SkippedEvent)
    assert "not observable" in skipped.reason
    assert planning.find_event(report, "M31") is None
    assert planning.find_event(report, "1P") is None  # not "161P"


def test_current_events_only_cover_nights_near_the_data(live_sources) -> None:
    """Brightness observed around 2026-10-04 says nothing about a night
    two months away — no list, an explanation instead."""
    far = datetime(2026, 12, 4, 10, 0, tzinfo=UTC)
    report = planning.current_events(SITE, SEESTAR, far)
    assert report.events == [] and report.skipped == []
    assert report.notes[0].startswith("Current events only cover nights within 14")
    # A week off is still fine.
    near = datetime(2026, 10, 11, 10, 0, tzinfo=UTC)
    assert planning.current_events(SITE, SEESTAR, near).events

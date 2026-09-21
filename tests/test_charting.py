"""Geometry tests for the shortlist-overview polar projection (pure
math, no charting library involved) — see nachtlotse/charting.py."""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from nachtlotse import charting, planning
from nachtlotse.data import store
from nachtlotse.engine import ephemeris
from nachtlotse.engine.models import HorizonProfile, Target, Verdict


def test_project_zenith_is_the_center() -> None:
    x, y = charting.project(90.0, az_deg=137.0)

    assert x == pytest.approx(0.0, abs=1e-9)
    assert y == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize(
    "az_deg,expected_xy",
    [
        (0.0, (0.0, 90.0)),  # North: top
        (90.0, (90.0, 0.0)),  # East: right
        (180.0, (0.0, -90.0)),  # South: bottom
        (270.0, (-90.0, 0.0)),  # West: left
    ],
)
def test_project_compass_directions_sit_on_the_rim(
    az_deg: float, expected_xy: tuple[float, float]
) -> None:
    x, y = charting.project(0.0, az_deg)

    assert x == pytest.approx(expected_xy[0], abs=1e-9)
    assert y == pytest.approx(expected_xy[1], abs=1e-9)


def test_grid_ring_is_a_closed_circle_at_the_expected_radius() -> None:
    points = charting.grid_ring(alt_deg=20.0)

    assert points[0] == pytest.approx(points[-1])
    expected_radius = 90.0 - 20.0
    for x, y in points:
        assert math.hypot(x, y) == pytest.approx(expected_radius, abs=1e-6)


def test_horizon_wedge_matches_the_rim_for_a_flat_horizon() -> None:
    site = store.default_site_record().site
    flat = HorizonProfile(points=[(0.0, 0.0), (360.0, 0.0)])
    flat_site = replace(site, horizon=flat)

    wedge = charting.horizon_wedge(flat_site)
    half = len(wedge) // 2
    outer, inner = wedge[:half], wedge[half:]

    assert len(outer) == len(inner)
    # A flat (zero everywhere) horizon means the "blocked" ring has zero
    # width: the inner boundary sits exactly on the rim, same as the outer.
    for (ox, oy), (ix, iy) in zip(outer, reversed(inner)):
        assert (ix, iy) == pytest.approx((ox, oy), abs=1e-6)


def test_horizon_wedge_follows_an_obstructed_sector() -> None:
    site = store.default_site_record().site
    obstructed = replace(
        site, horizon=HorizonProfile(points=[(0.0, 0.0), (90.0, 30.0), (360.0, 0.0)])
    )

    wedge = charting.horizon_wedge(obstructed, resolution_deg=10.0)
    half = len(wedge) // 2
    outer, inner = wedge[:half], wedge[half:]

    # Somewhere in the obstructed sector, the inner boundary must sit
    # strictly closer to the center than the rim (a real blocked band).
    assert any(
        math.hypot(*ix) < math.hypot(*ox) - 1.0 for ox, ix in zip(outer, reversed(inner))
    )


def test_shortlist_tracks_clips_below_horizon_and_splits_into_segments(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A target that dips below the horizon partway through the window
    must not have its above-horizon arcs joined through the ground."""
    site = store.default_site_record().site
    rig = store.default_rig_record().rig
    target = Target(name="test target", ra_deg=10.0, dec_deg=20.0)

    base = datetime(2026, 6, 1, 22, 0, tzinfo=UTC)
    # alt_deg pattern: below, below, above, above, above, below, below —
    # one contiguous above-horizon run in the middle.
    fake_series = [
        (base + timedelta(hours=i), ephemeris.AltAz(alt_deg=alt, az_deg=az, distance_au=1.0))
        for i, (alt, az) in enumerate(
            [(-5.0, 10.0), (-2.0, 20.0), (5.0, 30.0), (10.0, 40.0), (5.0, 50.0), (-3.0, 60.0), (-8.0, 70.0)]
        )
    ]
    monkeypatch.setattr(
        charting.ephemeris,
        "altitude_series",
        lambda *args, **kwargs: fake_series,
    )

    ranked = planning.RankedTarget(
        target=target,
        best_time=base,
        pos=ephemeris.AltAz(10.0, 40.0, 1.0),
        fit=1.0,
        reach=1.0,
    )
    entry = planning.ShortlistEntry(ranked=ranked, verdict=Verdict(level="GO", reasons=[]))
    plan = planning.NightPlan(
        site=site,
        rig=rig,
        evening_start=base,
        morning_end=base + timedelta(hours=6),
        moon_illumination_pct=0.0,
        moonrise=None,
        moonset=None,
        weather=None,
        hourly_cloud_cover=[],
        ranked=[ranked],
        shortlist=[entry],
    )

    tracks = charting.shortlist_tracks(plan)

    assert len(tracks) == 1
    (track,) = tracks
    assert track.name == "test target"
    assert len(track.segments) == 1
    (segment,) = track.segments
    assert len(segment) == 3  # the three above-horizon samples
    for x, y in segment:
        assert math.hypot(x, y) <= 90.0 + 1e-9


def test_moon_track_clips_below_horizon_and_splits_into_segments(
    template_sites: list[store.SiteRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same clipping/splitting contract as `shortlist_tracks`, for the
    Moon's own path (`engine.ephemeris.moon_altaz_series`, a real
    solar-system body, not a catalog `Target`)."""
    site = store.default_site_record().site
    base = datetime(2026, 6, 1, 22, 0, tzinfo=UTC)
    fake_series = [
        (base + timedelta(hours=i), ephemeris.AltAz(alt_deg=alt, az_deg=az, distance_au=0.0025))
        for i, (alt, az) in enumerate(
            [(-5.0, 10.0), (-2.0, 20.0), (5.0, 30.0), (10.0, 40.0), (5.0, 50.0), (-3.0, 60.0), (-8.0, 70.0)]
        )
    ]
    monkeypatch.setattr(
        charting.ephemeris,
        "moon_altaz_series",
        lambda *args, **kwargs: fake_series,
    )

    track = charting.moon_track(site, base, base + timedelta(hours=6))

    assert track.name == "Moon"
    assert len(track.segments) == 1
    (segment,) = track.segments
    assert len(segment) == 3
    for x, y in segment:
        assert math.hypot(x, y) <= 90.0 + 1e-9


def test_shortlist_tracks_draws_a_single_line_for_a_group_not_one_per_member(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A `RankedGroup`'s track is one line from its centroid position
    (`engine.grouping.centroid_target`), not one overlaid curve per
    member — members are co-visible/close together by construction, so
    stacking near-identical curves just clutters the chart, and one
    legend entry/color for the whole group already implies one line
    (`SHORTLIST_PALETTE` has a slot per shortlist entry, not per
    target)."""
    site = store.default_site_record().site
    rig = store.default_rig_record().rig
    target_a = Target(name="group member a", ra_deg=10.0, dec_deg=20.0)
    target_b = Target(name="group member b", ra_deg=10.1, dec_deg=20.0)

    base = datetime(2026, 6, 1, 22, 0, tzinfo=UTC)
    always_above_horizon = [
        (base + timedelta(hours=i), ephemeris.AltAz(alt_deg=30.0, az_deg=40.0, distance_au=1.0))
        for i in range(3)
    ]
    calls: list[Target] = []

    def fake_altitude_series(_site, target, *_args, **_kwargs):
        calls.append(target)
        return always_above_horizon

    monkeypatch.setattr(charting.ephemeris, "altitude_series", fake_altitude_series)

    ranked = planning.RankedGroup(
        targets=(target_a, target_b),
        best_time=base,
        pos=ephemeris.AltAz(30.0, 40.0, 1.0),
        fit=1.0,
        reach=1.0,
    )
    entry = planning.ShortlistEntry(ranked=ranked, verdict=Verdict(level="GO", reasons=[]))
    plan = planning.NightPlan(
        site=site,
        rig=rig,
        evening_start=base,
        morning_end=base + timedelta(hours=3),
        moon_illumination_pct=0.0,
        moonrise=None,
        moonset=None,
        weather=None,
        hourly_cloud_cover=[],
        ranked=[ranked],
        shortlist=[entry],
    )

    tracks = charting.shortlist_tracks(plan)

    assert len(tracks) == 1
    (track,) = tracks
    # The legend/name still names every member ...
    assert track.name == "group member a + group member b"
    # ... but the plotted line itself came from one altitude_series call
    # (the centroid), not one per member.
    assert len(calls) == 1
    assert calls[0] not in (target_a, target_b)
    assert len(track.segments) == 1
    assert len(track.segments[0]) == 3

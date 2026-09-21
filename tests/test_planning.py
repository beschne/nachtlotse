from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from astropy.time import Time

from nachtlotse import planning
from nachtlotse.data import store
from nachtlotse.engine import framing


def test_rank_targets_is_sorted_by_descending_priority_score_and_passes_constraints(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
) -> None:
    site = store.default_site_record().site
    rig = store.default_rig_record().rig
    ranked = planning.rank_targets(site, rig, datetime.now(UTC))
    scores = [
        framing.target_priority_score(row.pos.alt_deg, row.fit, row.reach)
        for row in ranked
    ]

    assert scores == sorted(scores, reverse=True)
    assert all(row.pos.alt_deg > 0.0 for row in ranked)


def test_rank_targets_types_filter_keeps_only_matching_categories(
    template_sites: list[store.SiteRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nachtlotse.engine.constraints import build_observer
    from nachtlotse.engine.models import Target

    site = store.get_site_record("Großer Feldberg").site  # unrestricted horizon
    rig = store.default_rig_record().rig
    observer = build_observer(site)
    night_reference = Time(datetime(2026, 9, 12, 22, 0, tzinfo=UTC))
    lst_deg = night_reference.sidereal_time(
        "apparent", longitude=observer.location.lon
    ).deg

    a_galaxy = Target(
        name="test galaxy",
        ra_deg=lst_deg,
        dec_deg=site.lat_deg - 20.0,
        types=("galaxy",),
    )
    a_cluster = Target(
        name="test cluster",
        ra_deg=lst_deg,
        dec_deg=site.lat_deg - 30.0,
        types=("open_cluster",),
    )
    monkeypatch.setattr(planning, "CATALOG", [a_galaxy, a_cluster])

    when = night_reference.to_datetime(timezone=UTC)
    galaxies_only = planning.rank_targets(site, rig, when, types=frozenset({"galaxy"}))

    assert [row.target.name for row in galaxies_only] == ["test galaxy"]


def test_rank_targets_lets_framing_fit_veto_a_high_but_poorly_framed_target(
    template_sites: list[store.SiteRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression test for the real case `target_priority_score` exists for:
    a tiny planetary nebula transiting near the zenith must rank below a
    well-framed target lower in the sky, not above it just for having the
    higher raw altitude (see engine.framing.target_priority_score).
    """
    from nachtlotse.engine.constraints import build_observer
    from nachtlotse.engine.models import Mount, Optics, Rig, Sensor, Target

    site = store.get_site_record("Großer Feldberg").site  # unrestricted horizon
    observer = build_observer(site)
    night_reference = Time(datetime(2026, 9, 12, 22, 0, tzinfo=UTC))
    lst_deg = night_reference.sidereal_time(
        "apparent", longitude=observer.location.lon
    ).deg

    rig = Rig(
        name="Wide-Field Test Rig",
        optics=Optics(name="Test Optics", focal_length_mm=250.0, aperture_mm=50.0),
        sensor=Sensor(name="Test Sensor", width_px=4000, height_px=3000, pixel_um=3.0),
        mount=Mount(name="EQ Test Mount", kind="eq"),  # sidesteps rotation gating
    )
    fov_width_deg, fov_height_deg = rig.fov_deg
    fov_short_arcmin = min(fov_width_deg, fov_height_deg) * 60.0

    tiny_near_zenith = Target(
        name="tiny near-zenith test target",
        ra_deg=lst_deg,
        dec_deg=site.lat_deg - 0.5,  # transits within ~0.5 deg of the zenith
        size_arcmin=(fov_short_arcmin * 0.01, fov_short_arcmin * 0.01),  # fit ~0.05
    )
    well_framed_lower = Target(
        name="well-framed lower test target",
        ra_deg=lst_deg,
        dec_deg=site.lat_deg - 40.0,  # transits well off zenith, still high enough
        size_arcmin=(fov_short_arcmin * 0.5, fov_short_arcmin * 0.3),  # fit 1.0
    )
    monkeypatch.setattr(planning, "CATALOG", [tiny_near_zenith, well_framed_lower])

    ranked = planning.rank_targets(site, rig, night_reference.to_datetime(timezone=UTC))

    assert [row.target.name for row in ranked] == [
        "well-framed lower test target",
        "tiny near-zenith test target",
    ]


def test_a_heavily_obstructed_horizon_excludes_targets_a_clear_horizon_admits(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
) -> None:
    """M2 DoD: the same sky yields different target lists at two sites with
    different horizons. Both sites share the built-in Feldberg's location —
    only the horizon profile differs.
    """
    from nachtlotse.engine.models import HorizonProfile

    now = datetime.now(UTC)
    rig = store.default_rig_record().rig
    base_site = store.get_site_record("Großer Feldberg").site
    open_site = base_site
    walled_site = replace(
        base_site, horizon=HorizonProfile(points=store._sector_to_points(348.0, 105.0))
    )

    def catalog_ids(ranked: list[planning.RankedEntry]) -> set[str]:
        ids: set[str] = set()
        for row in ranked:
            targets = row.targets if isinstance(row, planning.RankedGroup) else (row.target,)
            ids.update(target.catalog_id for target in targets)
        return ids

    open_ranked = catalog_ids(planning.rank_targets(open_site, rig, now))
    walled_ranked = catalog_ids(planning.rank_targets(walled_site, rig, now))

    assert open_ranked != walled_ranked


def test_rank_targets_folds_a_co_visible_pair_into_one_group(
    template_sites: list[store.SiteRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two targets close enough to share one frame of the rig, and
    simultaneously observable, become a single `RankedGroup` — replacing
    their individual `RankedTarget` entries rather than sitting alongside
    them (see engine.grouping and planning._fold_in_groups)."""
    from nachtlotse.engine import ephemeris, grouping
    from nachtlotse.engine.constraints import build_observer
    from nachtlotse.engine.models import Mount, Optics, Rig, Sensor, Target

    site = store.get_site_record("Großer Feldberg").site  # unrestricted horizon
    observer = build_observer(site)
    night_reference = Time(datetime(2026, 9, 12, 22, 0, tzinfo=UTC))
    lst_deg = night_reference.sidereal_time(
        "apparent", longitude=observer.location.lon
    ).deg

    rig = Rig(
        name="Wide-Field Test Rig",
        optics=Optics(name="Test Optics", focal_length_mm=250.0, aperture_mm=50.0),
        sensor=Sensor(name="Test Sensor", width_px=4000, height_px=3000, pixel_um=3.0),
        mount=Mount(name="EQ Test Mount", kind="eq"),  # sidesteps rotation gating
    )
    fov_short_arcmin = min(rig.fov_deg) * 60.0

    close_a = Target(name="close a", ra_deg=lst_deg, dec_deg=site.lat_deg - 20.0)
    close_b = Target(
        name="close b",
        ra_deg=lst_deg + (fov_short_arcmin * 0.3) / 60.0,
        dec_deg=site.lat_deg - 20.0,
    )
    far = Target(name="far", ra_deg=lst_deg, dec_deg=site.lat_deg - 60.0)
    monkeypatch.setattr(planning, "CATALOG", [close_a, close_b, far])

    ranked = planning.rank_targets(
        site, rig, night_reference.to_datetime(timezone=UTC)
    )

    groups = [row for row in ranked if isinstance(row, planning.RankedGroup)]
    singles = [row for row in ranked if isinstance(row, planning.RankedTarget)]

    assert len(groups) == 1
    assert {t.name for t in groups[0].targets} == {"close a", "close b"}
    assert [row.target.name for row in singles] == ["far"]

    group = groups[0]
    assert group.fit == pytest.approx(grouping.group_framing_score(rig, group.targets))
    assert group.pos.alt_deg == pytest.approx(
        min(
            ephemeris.altaz(site, member, group.best_time).alt_deg
            for member in group.targets
        )
    )


def test_rank_targets_leaves_distant_targets_ungrouped(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Targets too far apart for the rig's field of view stay as separate
    `RankedTarget` entries — grouping is opt-in by geometry, not assumed."""
    from nachtlotse.engine.constraints import build_observer
    from nachtlotse.engine.models import Target

    site = store.get_site_record("Großer Feldberg").site  # unrestricted horizon
    rig = store.default_rig_record().rig
    observer = build_observer(site)
    night_reference = Time(datetime(2026, 9, 12, 22, 0, tzinfo=UTC))
    lst_deg = night_reference.sidereal_time(
        "apparent", longitude=observer.location.lon
    ).deg

    a = Target(name="test a", ra_deg=lst_deg, dec_deg=site.lat_deg - 20.0)
    b = Target(name="test b", ra_deg=lst_deg, dec_deg=site.lat_deg - 60.0)
    monkeypatch.setattr(planning, "CATALOG", [a, b])

    ranked = planning.rank_targets(
        site, rig, night_reference.to_datetime(timezone=UTC)
    )

    assert all(isinstance(row, planning.RankedTarget) for row in ranked)
    assert {row.target.name for row in ranked} == {"test a", "test b"}


def _narrow_and_wide_test_rigs():
    from nachtlotse.engine.models import Mount, Optics, Rig, Sensor

    sensor = Sensor(name="Test Sensor", width_px=4000, height_px=3000, pixel_um=3.0)
    narrow = Rig(
        name="Narrow Test Rig",
        optics=Optics(name="Narrow Optics", focal_length_mm=1000.0, aperture_mm=150.0),
        sensor=sensor,
        mount=Mount(name="EQ Test Mount", kind="eq"),
    )
    wide = Rig(
        name="Wide Test Rig",
        optics=Optics(name="Wide Optics", focal_length_mm=100.0, aperture_mm=30.0),
        sensor=sensor,
        mount=Mount(name="EQ Test Mount", kind="eq"),  # sidesteps rotation gating
    )
    return narrow, wide


def test_rank_targets_for_best_rig_picks_the_better_framing_rig_per_target(
    template_sites: list[store.SiteRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The best-rig chooser: a small target should win with the
    narrow/long-focal-length rig (higher fill fraction), a large target
    with the wide one — not the same rig for both."""
    from nachtlotse.engine.constraints import build_observer
    from nachtlotse.engine.models import Target

    site = store.get_site_record("Großer Feldberg").site  # unrestricted horizon
    narrow_rig, wide_rig = _narrow_and_wide_test_rigs()
    observer = build_observer(site)
    night_reference = Time(datetime(2026, 9, 12, 22, 0, tzinfo=UTC))
    lst_deg = night_reference.sidereal_time(
        "apparent", longitude=observer.location.lon
    ).deg

    narrow_fov_short_arcmin = min(narrow_rig.fov_deg) * 60.0
    wide_fov_short_arcmin = min(wide_rig.fov_deg) * 60.0
    assert narrow_fov_short_arcmin < wide_fov_short_arcmin  # sanity check the fixture

    small_target = Target(
        name="small test target",
        ra_deg=lst_deg,
        dec_deg=site.lat_deg - 20.0,
        # Fits the narrow rig well (fit 1.0) but is a speck in the wide one.
        size_arcmin=(narrow_fov_short_arcmin * 0.9, narrow_fov_short_arcmin * 0.7),
    )
    large_target = Target(
        name="large test target",
        ra_deg=lst_deg,
        dec_deg=site.lat_deg - 40.0,
        # Fits the wide rig well but clips badly in the narrow one.
        size_arcmin=(wide_fov_short_arcmin * 0.9, wide_fov_short_arcmin * 0.7),
    )
    monkeypatch.setattr(planning, "CATALOG", [small_target, large_target])

    ranked = planning.rank_targets_for_best_rig(
        site, [narrow_rig, wide_rig], night_reference.to_datetime(timezone=UTC)
    )

    by_name = {row.target.name: row for row in ranked}
    assert by_name["small test target"].rig.name == "Narrow Test Rig"
    assert by_name["large test target"].rig.name == "Wide Test Rig"


def test_rank_targets_for_best_rig_drops_a_target_no_configured_rig_can_observe(
    template_sites: list[store.SiteRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nachtlotse.engine.models import Target

    site = store.get_site_record("Großer Feldberg").site
    narrow_rig, wide_rig = _narrow_and_wide_test_rigs()

    never_up = Target(name="never up test target", ra_deg=0.0, dec_deg=-89.0)
    monkeypatch.setattr(planning, "CATALOG", [never_up])

    ranked = planning.rank_targets_for_best_rig(
        site, [narrow_rig, wide_rig], datetime.now(UTC)
    )

    assert ranked == []


def test_plan_night_for_best_rig_carries_a_rig_per_shortlisted_target(
    template_sites: list[store.SiteRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nachtlotse.engine.constraints import build_observer
    from nachtlotse.engine.models import Target

    site = store.get_site_record("Großer Feldberg").site
    narrow_rig, wide_rig = _narrow_and_wide_test_rigs()
    observer = build_observer(site)
    night_reference = Time(datetime(2026, 9, 12, 22, 0, tzinfo=UTC))
    lst_deg = night_reference.sidereal_time(
        "apparent", longitude=observer.location.lon
    ).deg

    target = Target(
        name="best-rig plan test target", ra_deg=lst_deg, dec_deg=site.lat_deg - 20.0
    )
    monkeypatch.setattr(planning, "CATALOG", [target])

    plan = planning.plan_night_for_best_rig(
        site, [narrow_rig, wide_rig], night_reference.to_datetime(timezone=UTC)
    )

    assert len(plan.shortlist) == 1
    entry = plan.shortlist[0]
    assert entry.ranked.target.name == "best-rig plan test target"
    assert entry.ranked.rig.name in {"Narrow Test Rig", "Wide Test Rig"}
    assert entry.verdict.level in {"GO", "MARGINAL", "SKIP"}


def test_altaz_rig_devalues_a_near_zenith_target_that_an_eq_rig_keeps_at_peak(
    template_sites: list[store.SiteRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M3 DoD: a near-zenith target is downgraded for the alt-az mount, but
    not for a (hypothetical) eq rig — same site, same target, same time.
    """
    from nachtlotse.engine.constraints import build_fixed_target, build_observer
    from nachtlotse.engine.models import Mount, Optics, Rig, Sensor, Target

    site = store.get_site_record("Großer Feldberg").site  # unrestricted horizon
    observer = build_observer(site)

    # A reference known to fall within an astronomical-twilight dark window
    # at this latitude (established in test_constraints.py); the target's
    # RA is set to the LST there, so its transit lands at night too.
    night_reference = Time(datetime(2026, 9, 12, 22, 0, tzinfo=UTC))
    lst_deg = night_reference.sidereal_time(
        "apparent", longitude=observer.location.lon
    ).deg
    near_zenith_target = Target(
        name="near-zenith test target", ra_deg=lst_deg, dec_deg=site.lat_deg - 0.5
    )
    monkeypatch.setattr(planning, "CATALOG", [near_zenith_target])

    t_transit = observer.target_meridian_transit_time(
        night_reference, build_fixed_target(near_zenith_target), which="nearest"
    )
    reference = t_transit.to_datetime(timezone=UTC) - timedelta(hours=1)

    shared = {
        "optics": Optics(name="Test Optics", focal_length_mm=250.0, aperture_mm=50.0),
        "sensor": Sensor(
            name="Test Sensor", width_px=4000, height_px=3000, pixel_um=3.0
        ),
    }
    altaz_rig = Rig(
        name="Alt-Az Test Rig",
        mount=Mount(name="Alt-Az Test Mount", kind="altaz"),
        **shared,
    )
    eq_rig = Rig(
        name="EQ Test Rig", mount=Mount(name="EQ Test Mount", kind="eq"), **shared
    )

    altaz_ranked = planning.rank_targets(site, altaz_rig, reference)
    eq_ranked = planning.rank_targets(site, eq_rig, reference)

    eq_alt = eq_ranked[0].pos.alt_deg
    assert eq_alt > 89.0  # eq rig gets to use the true, near-zenith peak

    if altaz_ranked:
        assert altaz_ranked[0].pos.alt_deg < eq_alt  # pushed off the unsafe peak
    # else: fully excluded for the night — also a valid "devalued" outcome.


def test_plan_night_carries_dark_window_moon_weather_and_a_shortlist(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
) -> None:
    site = store.default_site_record().site
    rig = store.default_rig_record().rig
    now = datetime.now(UTC)

    plan = planning.plan_night(site, rig, now)

    assert plan.evening_start < plan.morning_end
    assert 0.0 <= plan.moon_illumination_pct <= 100.0
    assert plan.weather is not None  # offline fixture always provides one
    assert plan.hourly_cloud_cover, "the offline clear-sky fixture spans any dark window"
    assert all(
        plan.evening_start <= hour.when <= plan.morning_end
        for hour in plan.hourly_cloud_cover
    )
    assert plan.ranked, "the default site/rig should have observable targets tonight"
    assert plan.shortlist, "a non-empty ranking should yield a shortlist"
    # The top SHORTLIST_SIZE are always exactly ranked[:SHORTLIST_SIZE];
    # against the real catalog (unlike the synthetic ones elsewhere in
    # this file) a favorite outside that cutoff — e.g. T CrB, whose fit
    # score is always ~0 as a point source — can legitimately push the
    # shortlist longer, so this doesn't assert an upper bound or a plain
    # slice equality the way it did before favorites existed.
    shortlisted = [entry.ranked for entry in plan.shortlist]
    assert shortlisted[: planning.SHORTLIST_SIZE] == plan.ranked[: planning.SHORTLIST_SIZE]
    for extra in shortlisted[planning.SHORTLIST_SIZE :]:
        assert planning.is_favorite(extra)
    for entry in plan.shortlist:
        assert entry.verdict.level in ("GO", "MARGINAL", "SKIP")


def test_fetch_hourly_cloud_cover_clips_to_the_dark_window(
    template_sites: list[store.SiteRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nachtlotse.weather import open_meteo

    site = store.default_site_record().site
    base = datetime(2026, 9, 12, 18, 0, tzinfo=UTC)

    def fake_fetch_hourly(lat_deg: float, lon_deg: float) -> list[open_meteo.HourlyWeather]:
        return [
            open_meteo.HourlyWeather(
                when=base + timedelta(hours=offset),
                cloud_cover_pct=float(offset),  # distinct per hour, easy to check order
                wind_speed_kmh=5.0,
                humidity_pct=50.0,
                dew_point_c=5.0,
                temperature_c=15.0,
            )
            for offset in range(12)
        ]

    monkeypatch.setattr(open_meteo, "fetch_hourly", fake_fetch_hourly)

    evening_start = base + timedelta(hours=3)
    morning_end = base + timedelta(hours=8)
    hourly = planning.fetch_hourly_cloud_cover(site, evening_start, morning_end)

    assert [hour.cloud_cover_pct for hour in hourly] == [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]


def test_fetch_hourly_cloud_cover_is_empty_when_weather_is_unavailable(
    template_sites: list[store.SiteRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nachtlotse.weather import open_meteo

    def always_unavailable(lat_deg: float, lon_deg: float) -> list:
        raise open_meteo.WeatherUnavailable("simulated: no network")

    monkeypatch.setattr(open_meteo, "fetch_hourly", always_unavailable)

    site = store.default_site_record().site
    now = datetime.now(UTC)
    assert planning.fetch_hourly_cloud_cover(site, now, now + timedelta(hours=8)) == []


def test_plan_night_has_no_shortlist_when_nothing_is_observable(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(planning, "CATALOG", [])

    site = store.default_site_record().site
    rig = store.default_rig_record().rig
    plan = planning.plan_night(site, rig, datetime.now(UTC))

    assert plan.ranked == []
    assert plan.shortlist == []


def test_plan_night_gives_each_shortlisted_target_its_own_verdict(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A shortlist is not one verdict for the night: two targets at
    different altitudes can land on different GO/MARGINAL/SKIP levels."""
    from nachtlotse.engine.constraints import build_observer
    from nachtlotse.engine.models import Target
    from nachtlotse.weather import open_meteo

    site = store.get_site_record("Großer Feldberg").site  # unrestricted horizon
    rig = store.default_rig_record().rig
    observer = build_observer(site)
    night_reference = Time(datetime(2026, 9, 12, 22, 0, tzinfo=UTC))
    lst_deg = night_reference.sidereal_time(
        "apparent", longitude=observer.location.lon
    ).deg

    # conftest's autouse clear-sky fixture anchors its forecast window on
    # the real `datetime.now()`, which doesn't cover this fixed 2026 test
    # date — without this, both targets fall back to "no weather forecast"
    # and get capped at MARGINAL regardless of altitude, masking the thing
    # this test checks. Re-anchor the same clear-sky forecast on the
    # reference night instead.
    def clear_sky_around_reference(lat_deg: float, lon_deg: float) -> list:
        base = night_reference.to_datetime(timezone=UTC).replace(
            minute=0, second=0, microsecond=0
        )
        return [
            open_meteo.HourlyWeather(
                when=base + timedelta(hours=offset),
                cloud_cover_pct=10.0,
                wind_speed_kmh=5.0,
                humidity_pct=50.0,
                dew_point_c=5.0,
                temperature_c=15.0,
            )
            for offset in range(-24, 72)
        ]

    monkeypatch.setattr(open_meteo, "fetch_hourly", clear_sky_around_reference)

    high_target = Target(
        name="high test target", ra_deg=lst_deg, dec_deg=site.lat_deg - 20.0
    )
    low_target = Target(
        name="low test target", ra_deg=lst_deg, dec_deg=site.lat_deg - 55.0
    )
    monkeypatch.setattr(planning, "CATALOG", [high_target, low_target])

    plan = planning.plan_night(site, rig, night_reference.to_datetime(timezone=UTC))

    assert [entry.ranked.target.name for entry in plan.shortlist] == [
        "high test target",
        "low test target",
    ]
    high_entry, low_entry = plan.shortlist
    assert high_entry.verdict.level != low_entry.verdict.level


def test_is_favorite_checks_the_underlying_target_or_group_members() -> None:
    from nachtlotse.engine import ephemeris
    from nachtlotse.engine.models import Target

    now = datetime.now(UTC)
    pos = ephemeris.AltAz(alt_deg=0.0, az_deg=0.0, distance_au=0.0)
    plain = Target(name="plain", ra_deg=0.0, dec_deg=0.0)
    starred = Target(name="starred", ra_deg=0.0, dec_deg=0.0, favorite=True)

    assert (
        planning.is_favorite(
            planning.RankedTarget(target=plain, best_time=now, pos=pos, fit=0.0, reach=0.0)
        )
        is False
    )
    assert (
        planning.is_favorite(
            planning.RankedTarget(target=starred, best_time=now, pos=pos, fit=0.0, reach=0.0)
        )
        is True
    )
    # A group counts as a favorite if any one member does — same "any
    # member" convention cli.py's _entry_types already uses for a
    # group's categories.
    assert (
        planning.is_favorite(
            planning.RankedGroup(
                targets=(plain, starred), best_time=now, pos=pos, fit=0.0, reach=0.0
            )
        )
        is True
    )
    assert (
        planning.is_favorite(
            planning.RankedGroup(targets=(plain,), best_time=now, pos=pos, fit=0.0, reach=0.0)
        )
        is False
    )


def test_plan_night_keeps_a_favorite_in_the_shortlist_past_the_normal_cutoff(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A favorite (T CrB's own reason for existing — see ROADMAP.md's
    "Favorites in the catalog") must still show up in the shortlist even
    when its score leaves it well outside SHORTLIST_SIZE."""
    from nachtlotse.engine.constraints import build_observer
    from nachtlotse.engine.models import Target

    site = store.get_site_record("Großer Feldberg").site  # unrestricted horizon
    rig = store.default_rig_record().rig
    observer = build_observer(site)
    night_reference = Time(datetime(2026, 9, 12, 22, 0, tzinfo=UTC))
    lst_deg = night_reference.sidereal_time(
        "apparent", longitude=observer.location.lon
    ).deg

    # SHORTLIST_SIZE higher-scoring, non-favorite targets, each nearer
    # zenith than the favorite below, so the favorite always ranks last.
    # Spaced 10° apart in declination (same RA) — well beyond the
    # default rig's ~4°x2° FOV, so engine.grouping doesn't fold any of
    # these into a co-visible RankedGroup; a group would still count as
    # a favorite via is_favorite's "any member" rule, but this test is
    # about the plain single-target fold-in, so it avoids that case.
    fillers = [
        Target(
            name=f"filler {i}",
            ra_deg=lst_deg,
            dec_deg=site.lat_deg - 5.0 - 10.0 * i,
            size_arcmin=(10.0, 10.0),
        )
        for i in range(planning.SHORTLIST_SIZE)
    ]
    favorite = Target(
        name="favorite variable",
        ra_deg=lst_deg,
        dec_deg=site.lat_deg - 55.0,  # max alt ~35° — below every filler
        size_arcmin=(0.05, 0.05),
        favorite=True,
    )
    monkeypatch.setattr(planning, "CATALOG", [*fillers, favorite])

    plan = planning.plan_night(site, rig, night_reference.to_datetime(timezone=UTC))

    assert len(plan.ranked) == planning.SHORTLIST_SIZE + 1
    assert plan.ranked[-1].target.name == "favorite variable", (
        "the favorite should rank last on altitude alone, to actually test "
        "the fold-in rather than it winning a normal top-N slot"
    )
    assert len(plan.shortlist) == planning.SHORTLIST_SIZE + 1
    assert plan.shortlist[-1].ranked.target.name == "favorite variable"
    assert planning.is_favorite(plan.shortlist[-1].ranked)


def test_rank_targets_limits_evaluated_count(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rank_targets with a limit should stop after evaluating N matching targets."""
    from unittest.mock import patch

    from nachtlotse.engine.models import Target

    site = store.get_site_record("Großer Feldberg").site
    rig = store.default_rig_record().rig

    targets = [
        Target(name=f"target {i}", ra_deg=0.0, dec_deg=0.0, types=("galaxy",))
        for i in range(20)
    ]
    monkeypatch.setattr(planning, "CATALOG", targets)

    call_count = 0

    def counting_best_time(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return None  # every target fails — but the call is still made

    with patch(
        "nachtlotse.planning.constraints.best_time_tonight", side_effect=counting_best_time
    ):
        ranked = planning.rank_targets(site, rig, datetime.now(UTC), limit=5)

    assert call_count == 5  # only 5 evaluated
    assert len(ranked) == 0  # all failed constraints


def test_rank_targets_limit_zero_evaluates_all(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rank_targets with limit=0 should evaluate every matching target."""
    from unittest.mock import patch

    from nachtlotse.engine.models import Target

    site = store.get_site_record("Großer Feldberg").site
    rig = store.default_rig_record().rig

    targets = [
        Target(name=f"target {i}", ra_deg=0.0, dec_deg=0.0, types=("galaxy",))
        for i in range(20)
    ]
    monkeypatch.setattr(planning, "CATALOG", targets)

    call_count = 0

    def counting_best_time(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return None

    with patch(
        "nachtlotse.planning.constraints.best_time_tonight", side_effect=counting_best_time
    ):
        ranked = planning.rank_targets(site, rig, datetime.now(UTC), limit=0)

    assert call_count == 20  # all 20 evaluated
    assert len(ranked) == 0


def test_rank_targets_default_limit_is_50(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rank_targets without a limit should evaluate at most DEFAULT_MAX_EVALUATED."""
    from unittest.mock import patch

    from nachtlotse.engine.models import Target

    site = store.get_site_record("Großer Feldberg").site
    rig = store.default_rig_record().rig

    targets = [
        Target(name=f"target {i}", ra_deg=0.0, dec_deg=0.0, types=("galaxy",))
        for i in range(100)
    ]
    monkeypatch.setattr(planning, "CATALOG", targets)

    call_count = 0

    def counting_best_time(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return None

    with patch(
        "nachtlotse.planning.constraints.best_time_tonight", side_effect=counting_best_time
    ):
        ranked = planning.rank_targets(site, rig, datetime.now(UTC))

    assert call_count == 50  # default limit
    assert len(ranked) == 0


def test_rank_targets_limit_exceeds_catalog(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rank_targets with limit > catalog size should not error."""
    from unittest.mock import patch

    from nachtlotse.engine.models import Target

    site = store.get_site_record("Großer Feldberg").site
    rig = store.default_rig_record().rig

    targets = [
        Target(name=f"target {i}", ra_deg=0.0, dec_deg=0.0, types=("galaxy",))
        for i in range(10)
    ]
    monkeypatch.setattr(planning, "CATALOG", targets)

    call_count = 0

    def counting_best_time(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return None

    with patch(
        "nachtlotse.planning.constraints.best_time_tonight", side_effect=counting_best_time
    ):
        ranked = planning.rank_targets(site, rig, datetime.now(UTC), limit=50)

    assert call_count == 10  # all evaluated (no error)
    assert len(ranked) == 0

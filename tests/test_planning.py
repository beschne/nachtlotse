from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from astropy.time import Time

from nachtlotse import planning
from nachtlotse.data import store


def test_rank_targets_is_sorted_by_descending_altitude_and_passes_constraints(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
) -> None:
    site = store.default_site_record().site
    rig = store.default_rig_record().rig
    ranked = planning.rank_targets(site, rig, datetime.now(UTC))
    altitudes = [row.pos.alt_deg for row in ranked]

    assert altitudes == sorted(altitudes, reverse=True)
    assert all(alt_deg > 0.0 for alt_deg in altitudes)


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

    open_ranked = {
        row.target.catalog_id for row in planning.rank_targets(open_site, rig, now)
    }
    walled_ranked = {
        row.target.catalog_id for row in planning.rank_targets(walled_site, rig, now)
    }

    assert open_ranked != walled_ranked


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


def test_plan_night_carries_dark_window_moon_weather_and_a_hero_verdict(
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
    assert plan.ranked, "the default site/rig should have observable targets tonight"
    assert plan.verdict is not None
    assert plan.verdict.level in ("GO", "MARGINAL", "SKIP")


def test_plan_night_has_no_verdict_when_nothing_is_observable(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(planning, "CATALOG", [])

    site = store.default_site_record().site
    rig = store.default_rig_record().rig
    plan = planning.plan_night(site, rig, datetime.now(UTC))

    assert plan.ranked == []
    assert plan.verdict is None

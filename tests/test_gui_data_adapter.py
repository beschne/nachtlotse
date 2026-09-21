"""Tests for nachtlotse/gui/data_adapter.py.

No PySide6 dependency here (the module itself has none) — this file runs
unconditionally, unlike anything that touches real Qt widgets.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from nachtlotse.data.store import RigRecord, SiteRecord
from nachtlotse.engine import ephemeris
from nachtlotse.engine.models import (
    HorizonProfile,
    Mount,
    Optics,
    Rig,
    Sensor,
    Site,
    Target,
    Verdict,
    WeatherSummary,
)
from nachtlotse.gui import data_adapter
from nachtlotse.planning import (
    BestRigShortlistEntry,
    NightPlan,
    NightPlanForBestRig,
    RankedGroup,
    RankedTarget,
    RankedTargetForBestRig,
    ShortlistEntry,
)

BERLIN = ZoneInfo("Europe/Berlin")

SITE = Site(
    name="Test Site",
    lat_deg=50.0,
    lon_deg=8.0,
    elevation_m=200.0,
    tz="Europe/Berlin",
    horizon=HorizonProfile(points=[]),
)

RIG = Rig(
    name="Test Rig",
    optics=Optics(name="Test Optics", focal_length_mm=250.0, aperture_mm=50.0),
    sensor=Sensor(name="Test Sensor", width_px=4000, height_px=3000, pixel_um=3.0),
    mount=Mount(name="EQ Test Mount", kind="eq"),
)

OTHER_RIG = Rig(
    name="Other Test Rig",
    optics=Optics(name="Other Optics", focal_length_mm=500.0, aperture_mm=80.0),
    sensor=Sensor(name="Test Sensor", width_px=4000, height_px=3000, pixel_um=3.0),
    mount=Mount(name="EQ Test Mount", kind="eq"),
)

_WHEN = datetime(2026, 9, 20, 22, 0, tzinfo=UTC)

_TARGET_A = Target(
    name="target a", catalog_id="TA1", ra_deg=10.0, dec_deg=20.0, types=("galaxy",)
)
_TARGET_B = Target(
    name="target b", catalog_id="TB2", ra_deg=11.0, dec_deg=20.0, types=("open_cluster",)
)

_WEATHER = WeatherSummary(
    max_cloud_cover_pct=15.0,
    avg_cloud_cover_pct=8.0,
    max_wind_kmh=12.0,
    min_dew_point_spread_c=3.5,
)


def _pos(alt_deg: float, az_deg: float) -> ephemeris.AltAz:
    return ephemeris.AltAz(alt_deg=alt_deg, az_deg=az_deg, distance_au=1.0)


def _night_plan(shortlist_ranked) -> NightPlan:
    shortlist = [
        ShortlistEntry(row, Verdict(level="GO", reasons=["clear sky and good conditions"]))
        for row in shortlist_ranked
    ]
    return NightPlan(
        site=SITE,
        rig=RIG,
        evening_start=_WHEN,
        morning_end=_WHEN,
        moon_illumination_pct=42.0,
        moonrise=None,
        moonset=None,
        weather=_WEATHER,
        hourly_cloud_cover=[],
        ranked=list(shortlist_ranked),
        shortlist=shortlist,
    )


def test_entry_label_joins_a_ranked_groups_member_names() -> None:
    group = RankedGroup(
        targets=(_TARGET_A, _TARGET_B), best_time=_WHEN, pos=_pos(60.0, 90.0), fit=0.8, reach=1.0
    )
    assert data_adapter.entry_label(group) == "TA1 target a, TB2 target b"


def test_entry_type_label_dedupes_a_groups_categories_in_first_seen_order() -> None:
    group = RankedGroup(
        targets=(_TARGET_A, _TARGET_B), best_time=_WHEN, pos=_pos(60.0, 90.0), fit=0.8, reach=1.0
    )
    assert data_adapter.entry_type_label(group) == "Galaxy/Open Cluster"


def test_build_shortlist_rows_covers_every_field() -> None:
    ranked = RankedTarget(
        target=_TARGET_A, best_time=_WHEN, pos=_pos(55.0, 180.0), fit=0.9, reach=1.0
    )
    plan = _night_plan([ranked])

    (row,) = data_adapter.build_shortlist_rows(plan, BERLIN)

    assert row.label == "TA1 target a"
    assert row.type_label == "Galaxy"
    assert row.alt_text == "55.0°"
    assert row.az_text == "180.0°"
    assert row.fit_text == "0.90"
    assert row.reach_text == "1.00"
    assert row.rig_name is None
    assert row.verdict_level == "GO"
    assert row.verdict_reasons == ("clear sky and good conditions",)


def test_build_ranked_rows_covers_the_full_ranked_list_with_no_verdict_field() -> None:
    shortlisted = RankedTarget(
        target=_TARGET_A, best_time=_WHEN, pos=_pos(55.0, 180.0), fit=0.9, reach=1.0
    )
    unshortlisted = RankedTarget(
        target=_TARGET_B, best_time=_WHEN, pos=_pos(10.0, 90.0), fit=0.2, reach=1.0
    )
    plan = _night_plan([shortlisted, unshortlisted])

    rows = data_adapter.build_ranked_rows(plan, BERLIN)

    assert [row.label for row in rows] == ["TA1 target a", "TB2 target b"]
    assert rows[0].alt_text == "55.0°"
    assert rows[0].rig_name is None
    assert not hasattr(rows[0], "verdict_level")


def test_build_shortlist_rows_names_each_entrys_own_rig_for_best_rig_plans() -> None:
    row = RankedTargetForBestRig(
        target=_TARGET_A, rig=OTHER_RIG, best_time=_WHEN, pos=_pos(70.0, 200.0), fit=1.0, reach=1.0
    )
    plan = NightPlanForBestRig(
        site=SITE,
        evening_start=_WHEN,
        morning_end=_WHEN,
        moon_illumination_pct=10.0,
        moonrise=None,
        moonset=None,
        weather=None,
        hourly_cloud_cover=[],
        ranked=[row],
        shortlist=[BestRigShortlistEntry(row, Verdict(level="MARGINAL", reasons=["x"]))],
    )

    (result,) = data_adapter.build_shortlist_rows(plan, BERLIN)

    assert result.rig_name == "Other Test Rig"


def test_weather_line_reports_unavailable_when_none() -> None:
    assert "unavailable" in data_adapter.weather_line(None)


def test_weather_line_includes_clouds_wind_and_dew_margin() -> None:
    line = data_adapter.weather_line(_WEATHER)
    assert "15%" in line
    assert "12" in line
    assert "3.5" in line


def test_build_header_summary_counts_verdicts_and_formats_the_dark_window() -> None:
    go_row = RankedTarget(
        target=_TARGET_A, best_time=_WHEN, pos=_pos(55.0, 180.0), fit=1.0, reach=1.0
    )
    skip_row = RankedTarget(
        target=_TARGET_B, best_time=_WHEN, pos=_pos(10.0, 90.0), fit=1.0, reach=1.0
    )
    plan = NightPlan(
        site=SITE,
        rig=RIG,
        evening_start=_WHEN,
        morning_end=_WHEN,
        moon_illumination_pct=66.0,
        moonrise=None,
        moonset=None,
        weather=_WEATHER,
        hourly_cloud_cover=[],
        ranked=[go_row, skip_row],
        shortlist=[
            ShortlistEntry(go_row, Verdict(level="GO", reasons=["fine"])),
            ShortlistEntry(skip_row, Verdict(level="SKIP", reasons=["too low"])),
        ],
    )

    summary = data_adapter.build_header_summary(plan, BERLIN)

    assert summary.moon_text == "66% illuminated"
    assert "1 GO" in summary.counts_text
    assert "1 skip" in summary.counts_text
    assert "2 shortlisted" in summary.counts_text
    assert "2026-09-21" in summary.dark_window_text  # UTC 22:00 -> next-day CEST


def test_build_header_summary_appends_whichever_moon_events_are_present() -> None:
    go_row = RankedTarget(
        target=_TARGET_A, best_time=_WHEN, pos=_pos(55.0, 180.0), fit=1.0, reach=1.0
    )
    base_plan = NightPlan(
        site=SITE,
        rig=RIG,
        evening_start=_WHEN,
        morning_end=_WHEN,
        moon_illumination_pct=66.0,
        moonrise=None,
        moonset=None,
        weather=_WEATHER,
        hourly_cloud_cover=[],
        ranked=[go_row],
        shortlist=[ShortlistEntry(go_row, Verdict(level="GO", reasons=["fine"]))],
    )

    both = data_adapter.build_header_summary(
        replace(base_plan, moonrise=_WHEN, moonset=_WHEN + timedelta(hours=8)), BERLIN
    )
    rise_only = data_adapter.build_header_summary(replace(base_plan, moonrise=_WHEN), BERLIN)
    neither = data_adapter.build_header_summary(base_plan, BERLIN)

    assert "rises" in both.moon_text and "sets" in both.moon_text
    assert "rises" in rise_only.moon_text and "sets" not in rise_only.moon_text
    assert neither.moon_text == "66% illuminated"


def test_build_site_info_covers_aliases_region_bortle_and_address() -> None:
    record = SiteRecord(
        site=SITE, region="Taunus", bortle="4", address="Somewhere 1", aliases=("Home",)
    )

    info = data_adapter.build_site_info(record)

    assert info.name == "Test Site"
    assert info.aliases_text == "Home"
    assert "50.00000" in info.coords_text
    assert "Taunus" in info.region_text and "Bortle 4" in info.region_text
    assert info.horizon_text == "Horizon: flat/sector"
    assert info.address == "Somewhere 1"


def test_build_site_info_leaves_optional_fields_empty_when_unset() -> None:
    record = SiteRecord(site=SITE, region="Taunus", bortle="4")

    info = data_adapter.build_site_info(record)

    assert info.aliases_text == ""
    assert info.address == ""


def test_build_rig_info_covers_optics_sensor_fov_and_limiting_magnitude() -> None:
    record = RigRecord(rig=RIG, aliases=("TestRig",))

    info = data_adapter.build_rig_info(record)

    assert info.name == "Test Rig"
    assert info.aliases_text == "TestRig"
    assert "250 mm f/5.0" in info.optics_text
    assert "4000×3000 px" in info.sensor_text
    assert "FoV" in info.fov_text
    assert "Bortle 2" in info.limiting_mag_text and "Bortle 5" in info.limiting_mag_text

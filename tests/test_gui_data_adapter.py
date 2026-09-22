"""Tests for nachtlotse/gui/data_adapter.py.

No PySide6 dependency here (the module itself has none) — this file runs
unconditionally, unlike anything that touches real Qt widgets.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from nachtlotse import best_sky
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
from nachtlotse.weather import open_meteo

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


_ZULU = SiteRecord(
    site=replace(SITE, name="Zulu Site", lat_deg=51.0),
    region="Alpha Region",
    bortle="4",
)
_ALPHA = SiteRecord(
    site=replace(SITE, name="Alpha Site", lat_deg=50.0),
    region="Beta Region",
    bortle="4",
)
_MID = SiteRecord(
    site=replace(SITE, name="Mid Site", lat_deg=50.5),
    region="Alpha Region",
    bortle="4",
)
# Deliberately not already in any sorted order.
_SORT_TEST_SITES = [_ZULU, _ALPHA, _MID]


def test_sort_sites_file_mode_keeps_the_given_order() -> None:
    rows = data_adapter.sort_sites(_SORT_TEST_SITES, "file")

    assert [row.site_record for row in rows] == _SORT_TEST_SITES
    assert all(row.distance_text is None for row in rows)


def test_sort_sites_region_mode_sorts_by_region_then_name() -> None:
    rows = data_adapter.sort_sites(_SORT_TEST_SITES, "region")

    # Alpha Region (Mid, Zulu — by name within the region) before Beta Region.
    assert [row.site_record.site.name for row in rows] == [
        "Mid Site",
        "Zulu Site",
        "Alpha Site",
    ]
    assert all(row.distance_text is None for row in rows)


def test_sort_sites_distance_mode_ranks_nearest_first_from_the_reference() -> None:
    rows = data_adapter.sort_sites(_SORT_TEST_SITES, "distance", reference=_ALPHA)

    # _ALPHA (lat 50.0) itself first (0 km), then _MID (50.5), then _ZULU (51.0).
    assert [row.site_record.site.name for row in rows] == [
        "Alpha Site",
        "Mid Site",
        "Zulu Site",
    ]
    assert rows[0].distance_text == "0 km"
    assert rows[1].distance_text is not None and "km" in rows[1].distance_text
    assert rows[1].distance_text != rows[2].distance_text


def test_sort_sites_distance_mode_requires_a_reference() -> None:
    with pytest.raises(ValueError, match="reference"):
        data_adapter.sort_sites(_SORT_TEST_SITES, "distance")


def test_sort_sites_regions_filters_before_sorting() -> None:
    """The `regions` filter is independent of `mode` (Sites tab's own
    REGIONS checkboxes, orthogonal to SORT) — file order is preserved
    here among the sites that pass the filter."""
    rows = data_adapter.sort_sites(_SORT_TEST_SITES, "file", regions={"Alpha Region"})

    assert [row.site_record.site.name for row in rows] == ["Zulu Site", "Mid Site"]


def test_sort_sites_regions_combines_with_region_sort() -> None:
    rows = data_adapter.sort_sites(_SORT_TEST_SITES, "region", regions={"Alpha Region"})

    assert [row.site_record.site.name for row in rows] == ["Mid Site", "Zulu Site"]


def test_sort_sites_empty_regions_set_excludes_every_site() -> None:
    """An empty set is a real filter result (nothing matches), not the
    same as `regions=None` (no filtering at all)."""
    assert data_adapter.sort_sites(_SORT_TEST_SITES, "file", regions=set()) == []


def test_sort_sites_regions_none_means_unfiltered() -> None:
    rows = data_adapter.sort_sites(_SORT_TEST_SITES, "file", regions=None)

    assert len(rows) == len(_SORT_TEST_SITES)


def _hourly(hours: list[tuple[int, float]]) -> list[open_meteo.HourlyWeather]:
    """(hour offset from 22:00 UTC, cloud_cover_pct) pairs -> a
    HourlyWeather list, for shared_hourly_axis tests below."""
    base = datetime(2026, 9, 22, 22, 0, tzinfo=UTC)
    return [
        open_meteo.HourlyWeather(
            when=base + timedelta(hours=offset),
            cloud_cover_pct=pct,
            wind_speed_kmh=5.0,
            humidity_pct=50.0,
            dew_point_c=5.0,
            temperature_c=15.0,
        )
        for offset, pct in hours
    ]


def test_shared_hourly_axis_spans_earliest_start_to_latest_end() -> None:
    short_night = _hourly([(0, 10.0), (1, 20.0)])  # 22:00, 23:00
    long_night = _hourly([(-1, 5.0), (0, 10.0), (1, 20.0), (2, 30.0)])  # 21:00..00:00

    axis = data_adapter.shared_hourly_axis([short_night, long_night])

    base = datetime(2026, 9, 22, 22, 0, tzinfo=UTC)
    assert axis == [base + timedelta(hours=h) for h in (-1, 0, 1, 2)]


def test_shared_hourly_axis_handles_empty_input() -> None:
    assert data_adapter.shared_hourly_axis([]) == []
    assert data_adapter.shared_hourly_axis([[], []]) == []


def test_build_best_sky_rows_covers_weather_distance_and_site_lookup() -> None:
    reference_record = SiteRecord(site=SITE, region="Taunus", bortle="4")
    other_site = replace(SITE, name="Other Site", lat_deg=51.0)
    other_record = SiteRecord(site=other_site, region="Hintertaunus", bortle="5")

    hourly = [
        open_meteo.HourlyWeather(
            when=datetime(2026, 9, 22, 22, 0, tzinfo=UTC),
            cloud_cover_pct=20.0,
            wind_speed_kmh=10.0,
            humidity_pct=50.0,
            dew_point_c=5.0,
            temperature_c=12.0,
        )
    ]
    reports = [
        best_sky.SiteSkyReport(
            site=other_site,
            distance_km=111.2,
            bearing_deg=0.0,
            weather=WeatherSummary(
                max_cloud_cover_pct=20.0,
                avg_cloud_cover_pct=5.0,
                max_wind_kmh=10.0,
                min_dew_point_spread_c=3.0,
            ),
            hourly_cloud_cover=hourly,
        ),
        best_sky.SiteSkyReport(
            site=SITE,
            distance_km=0.0,
            bearing_deg=None,
            weather=None,
            hourly_cloud_cover=[],
            weather_unavailable_reason="unreachable",
        ),
    ]

    rows = data_adapter.build_best_sky_rows(reports, [reference_record, other_record])

    assert rows[0].site_record is other_record
    assert rows[0].site_text == "Other Site, Hintertaunus"
    assert "111 km" in rows[0].distance_text and "N" in rows[0].distance_text
    assert "20%" in rows[0].clouds_text and "5%" in rows[0].clouds_text
    assert "up to" not in rows[0].clouds_text  # that phrasing lives in the column header
    assert rows[0].clouds_available is True
    assert rows[0].hourly_cloud_cover == hourly

    assert rows[1].site_record is reference_record
    assert rows[1].site_text == "Test Site, Taunus"
    assert rows[1].distance_text == "0 km"
    assert rows[1].clouds_text == "Weather unavailable"
    assert rows[1].clouds_available is False
    assert rows[1].hourly_cloud_cover == []


def test_build_best_sky_rows_distinguishes_beyond_forecast_horizon() -> None:
    """A date past Open-Meteo's own forecast horizon is a routine,
    expected case (picking a date weeks out), not a fetch failure — the
    two must read differently, not both collapse into one generic
    "unavailable" (see best_sky.WeatherUnavailableReason)."""
    record = SiteRecord(site=SITE, region="Taunus", bortle="4")
    report = best_sky.SiteSkyReport(
        site=SITE,
        distance_km=0.0,
        bearing_deg=None,
        weather=None,
        hourly_cloud_cover=[],
        weather_unavailable_reason="beyond_forecast_horizon",
    )

    (row,) = data_adapter.build_best_sky_rows([report], [record])

    assert row.clouds_text == "Beyond forecast range"
    assert row.clouds_available is False

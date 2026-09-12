from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from astropy.time import Time

from nachtlotse import cli
from nachtlotse.data import store


def test_plan_command_prints_dark_window_moon_and_a_ranked_table(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["plan"])
    assert exit_code == 0

    output = capsys.readouterr().out
    assert template_sites[0].site.name in output
    assert template_rigs[0].rig.name in output
    assert "Dark window:" in output
    assert "Moon:" in output
    assert "Weather:" in output
    assert "Verdict:" in output

    default_site = store.default_site_record().site
    default_rig = store.default_rig_record().rig
    ranked = cli._rank_targets(default_site, default_rig, datetime.now(UTC))
    for target, *_rest in ranked:
        assert target.catalog_id in output


def test_plan_command_accepts_a_site_by_name_or_alias(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["plan", "--site", "Sternwarte"]) == 0
    output = capsys.readouterr().out
    assert "Volkssternwarte Hochtaunus" in output


def test_plan_command_accepts_a_rig_by_name_or_alias(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["plan", "--rig", "S50P"]) == 0
    output = capsys.readouterr().out
    assert "ZWO Seestar S50 Pro" in output


def test_plan_command_accepts_a_date_and_uses_that_nights_dark_window(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["plan", "--date", "2026-11-14"])
    assert exit_code == 0

    output = capsys.readouterr().out
    assert "Dark window: 2026-11-14" in output
    # Weather is far beyond Open-Meteo's forecast horizon, so this must
    # fall back gracefully rather than error.
    assert "Weather: unavailable" in output
    assert "Verdict:" in output


def test_plan_command_rejects_a_malformed_date(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["plan", "--date", "14.11.2026"])
    assert exit_code == 2
    assert "Invalid --date" in capsys.readouterr().err


def test_plan_command_rejects_an_unknown_site(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["plan", "--site", "Nirgendwo"])
    assert exit_code == 2


def test_plan_command_rejects_an_unknown_rig(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["plan", "--rig", "Nichtvorhanden"])
    assert exit_code == 2


def test_plan_command_reports_the_setup_hint_when_no_sites_are_configured(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(store, "SITES", [])
    exit_code = cli.main(["plan"])
    assert exit_code == 2
    assert "No observing sites configured" in capsys.readouterr().err


def test_plan_command_reports_the_setup_hint_when_no_rigs_are_configured(
    template_sites: list[store.SiteRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(store, "RIGS", [])
    exit_code = cli.main(["plan"])
    assert exit_code == 2
    assert "No rigs configured" in capsys.readouterr().err


def test_rank_targets_is_sorted_by_descending_altitude_and_passes_constraints(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
) -> None:
    site = store.default_site_record().site
    rig = store.default_rig_record().rig
    ranked = cli._rank_targets(site, rig, datetime.now(UTC))
    altitudes = [pos.alt_deg for _target, _best_time, pos, _fit in ranked]

    assert altitudes == sorted(altitudes, reverse=True)
    assert all(alt_deg > 0.0 for alt_deg in altitudes)


def test_sites_command_lists_every_known_site(
    template_sites: list[store.SiteRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["sites"])
    assert exit_code == 0

    output = capsys.readouterr().out
    for record in template_sites:
        assert record.site.name in output


def test_sites_command_reports_the_setup_hint_when_nothing_is_configured(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(store, "SITES", [])
    exit_code = cli.main(["sites"])
    assert exit_code == 2
    assert "No observing sites configured" in capsys.readouterr().err


def test_rigs_command_lists_every_known_rig(
    template_rigs: list[store.RigRecord],
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["rigs"])
    assert exit_code == 0

    output = capsys.readouterr().out
    for record in template_rigs:
        assert record.rig.name in output


def test_rigs_command_reports_the_setup_hint_when_nothing_is_configured(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(store, "RIGS", [])
    exit_code = cli.main(["rigs"])
    assert exit_code == 2
    assert "No rigs configured" in capsys.readouterr().err


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
        target.catalog_id for target, *_ in cli._rank_targets(open_site, rig, now)
    }
    walled_ranked = {
        target.catalog_id for target, *_ in cli._rank_targets(walled_site, rig, now)
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
    monkeypatch.setattr(cli, "CATALOG", [near_zenith_target])

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

    altaz_ranked = cli._rank_targets(site, altaz_rig, reference)
    eq_ranked = cli._rank_targets(site, eq_rig, reference)

    eq_alt = eq_ranked[0][2].alt_deg
    assert eq_alt > 89.0  # eq rig gets to use the true, near-zenith peak

    if altaz_ranked:
        assert altaz_ranked[0][2].alt_deg < eq_alt  # pushed off the unsafe peak
    # else: fully excluded for the night — also a valid "devalued" outcome.


def test_plan_command_skips_on_overcast_weather(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """M4 DoD: overcast sky -> SKIP with the reason named in the output."""
    from nachtlotse.weather import open_meteo

    def overcast_everywhere(lat_deg: float, lon_deg: float) -> list:
        base = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        return [
            open_meteo.HourlyWeather(
                when=base + timedelta(hours=offset),
                cloud_cover_pct=95.0,
                wind_speed_kmh=5.0,
                humidity_pct=80.0,
                dew_point_c=5.0,
                temperature_c=15.0,
            )
            for offset in range(-24, 72)
        ]

    monkeypatch.setattr(open_meteo, "fetch_hourly", overcast_everywhere)

    assert cli.main(["plan"]) == 0
    output = capsys.readouterr().out

    assert "Verdict: SKIP" in output
    assert "cloud cover" in output.lower()


def test_plan_command_falls_back_gracefully_when_weather_is_unavailable(
    template_sites: list[store.SiteRecord],
    template_rigs: list[store.RigRecord],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Weather is an optional layer — no network must not break the ranking."""
    from nachtlotse.weather import open_meteo

    def always_unavailable(lat_deg: float, lon_deg: float) -> list:
        raise open_meteo.WeatherUnavailable("simulated: no network")

    monkeypatch.setattr(open_meteo, "fetch_hourly", always_unavailable)

    assert cli.main(["plan"]) == 0
    output = capsys.readouterr().out

    assert "Weather: unavailable" in output
    assert "Verdict:" in output  # still produced, from sky geometry alone
    assert "Best time (local)" in output  # the ranked table still printed


def test_unknown_command_is_rejected() -> None:
    with pytest.raises(SystemExit):
        cli.main(["nonsense"])

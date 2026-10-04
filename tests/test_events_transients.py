"""Supernovae and novae: Rochester's brightness list, TNS, and their
planning section — network always mocked.

The Rochester table rows mirror the real page's markup (2026-10-04); the
TNS CSV header is the real one from its search page.
"""

from __future__ import annotations

import urllib.error
from datetime import UTC, datetime, timedelta
from email.message import Message
from pathlib import Path

import pytest

from nachtlotse import planning
from nachtlotse.events import EventsUnavailable, _backoff, _http, rochester, tns
from tests.test_current_events import (  # noqa: F401 — live_sources is a fixture
    SEESTAR,
    SITE,
    WHEN,
    live_sources,
)

ROCHESTER_PAGE = """<html><body>
<b>All active supernova over mag 17.0</b>
<table>
<tr><th>Name</th><th>Mag</th><th>Type</th><th>Host</th></tr>
<tr><td><a href="#2026sqf" target="_self">2026sqf</a></td><td>12.5</td><td>Ia-CSM</td><td><a href="http://www.wikisky.org/?ra=10.646656&de=53.509472&zoom=10&show_box=1&box_width=50">NGC 3310</a></td></tr>
<tr><td><a href="#2026aaiv" target="_self">2026aaiv</a></td><td>13.0</td><td>Ia</td><td><a href="http://www.wikisky.org/?ra=22.618227&de=34.409824&zoom=10&show_box=1&box_width=50">NGC 7331</a></td></tr>
<tr><td><a href="novae.html#2026aaom" target="_self">AT2026aaom</a></td><td>15.3</td><td>EGN</td><td><a href="http://www.wikisky.org/?ra=0.713995&de=41.316322&zoom=10&show_box=1&box_width=50">M31</a></td></tr>
<tr><td><a href="#2026pub" target="_self">2026pub</a></td><td>16.0*</td><td>II</td><td><a href="http://www.wikisky.org/?ra=13.760411&de=-5.993286&zoom=10">MCG -1-35-10</a></td></tr>
<tr><td><a href="#2026zsr" target="_self">AT2026zsr</a></td><td>16.2*</td><td>unk</td><td><a href="http://www.wikisky.org/?ra=12.572152&de=36.511677&zoom=10">LEDA 4105377</a></td></tr>
<tr><td><a href="#2026yly" target="_self">2026yly</a></td><td>12.0</td><td>II</td><td>NGC 2748</td></tr>
</table>
* - last observation is over one month old.
</body></html>"""

TNS_HEADER = (
    '"ID","Name","RA","DEC","Obj. Type","Redshift","Host Name","Host Redshift",'
    '"Reporting Group/s","Discovery Data Source/s","Classifying Group/s",'
    '"Associated Group/s","Disc. Internal Name","Disc. Instrument/s",'
    '"Class. Instrument/s","TNS AT","Public","End Prop. Period",'
    '"Discovery Mag/Flux","Discovery Filter","Discovery Date (UT)","Sender",'
    '"Remarks","Unreal","Discovery Bibcode","Classification Bibcodes",'
    '"Ext. catalog/s","Auto classification"\n'
)


def _tns_row(name, ra, dec, obj_type, host, mag, date) -> str:
    cells = ["1", name, ra, dec, obj_type, "", host] + [""] * 11
    cells += [mag, "orange-ATLAS", date] + [""] * 7
    return ",".join(f'"{c}"' for c in cells) + "\n"


YLY_CSV = TNS_HEADER + _tns_row(
    "SN 2026yly", "09:13:43.2", "+76:28:31.0", "SN II", "NGC2748", "15.4", "2026-09-20"
)
NOVAE_CSV = (
    TNS_HEADER
    + _tns_row(
        "AT 2026abbx",
        "17:50:00.0",
        "-23:43:20.71",
        "Nova",
        "Milky Way",
        "12.6",
        "2026-09-08 04:00:00",
    )
    + _tns_row(
        "AT 2026aaom",
        "00:42:50.387",
        "+41:18:57.22",
        "Nova",
        "M31",
        "18.2",
        "2026-09-04 03:37:43.680",
    )
)


# --- Rochester ---------------------------------------------------------------


def test_parse_latest_supernovae_reads_the_active_table() -> None:
    table = rochester.parse_latest_supernovae(ROCHESTER_PAGE)

    assert set(table) == {
        "2026sqf",
        "2026aaiv",
        "2026aaom",
        "2026pub",
        "2026zsr",
        "2026yly",
    }
    aaiv = table["2026aaiv"]
    assert (aaiv.magnitude, aaiv.stale, aaiv.rochester_type, aaiv.host) == (
        13.0,
        False,
        "Ia",
        "NGC 7331",
    )
    # The host link is centered on the supernova itself — matches TNS's
    # 22:37:05.628 +34:24:35.19 to well under an arcsecond.
    assert aaiv.ra_deg == pytest.approx(339.27341, abs=1e-4)
    assert aaiv.dec_deg == pytest.approx(34.409824, abs=1e-6)
    assert table["2026aaom"].rochester_type == "EGN"  # "AT" prefix dropped
    assert table["2026pub"].stale and table["2026pub"].magnitude == 16.0
    assert table["2026yly"].ra_deg is None  # no link: TNS has to say


def test_parse_latest_supernovae_refuses_a_changed_layout() -> None:
    with pytest.raises(ValueError, match="not found"):
        rochester.parse_latest_supernovae("<html>redesigned</html>")


def test_fetch_transient_brightness_caches_and_backs_off_on_layout_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(_http, "get", lambda url, source: ROCHESTER_PAGE.encode())
    now = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
    first = rochester.fetch_transient_brightness(now=now, cache_dir=tmp_path)
    assert "2026aaiv" in first.transients

    calls = []
    monkeypatch.setattr(
        _http, "get", lambda url, source: calls.append(url) or b"<html>new</html>"
    )
    later = now + timedelta(hours=13)  # past the 12 h TTL
    stale = rochester.fetch_transient_brightness(now=later, cache_dir=tmp_path)
    again = rochester.fetch_transient_brightness(now=later, cache_dir=tmp_path)
    assert stale.fetched_at == again.fetched_at == now  # served from cache
    assert len(calls) == 1  # then held off
    assert stale.transients["2026aaiv"].ra_deg == pytest.approx(339.27341, abs=1e-4)


# --- TNS ---------------------------------------------------------------------


def test_parse_search_csv_reads_the_real_columns() -> None:
    (yly,) = tns.parse_search_csv(YLY_CSV)
    assert (yly.objname, yly.name, yly.tns_type, yly.host) == (
        "2026yly",
        "SN 2026yly",
        "SN II",
        "NGC2748",
    )
    assert yly.ra_deg == pytest.approx((9 + 13 / 60 + 43.2 / 3600) * 15)
    assert yly.dec_deg == pytest.approx(76 + 28 / 60 + 31 / 3600)
    assert yly.discovery_mag == 15.4
    assert yly.classified

    novae = tns.parse_search_csv(NOVAE_CSV)
    assert novae[0].dec_deg == pytest.approx(-(23 + 43 / 60 + 20.71 / 3600))


def test_lookup_objects_caches_classified_objects_for_good(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []
    monkeypatch.setattr(
        _http, "get", lambda url, source: calls.append(url) or YLY_CSV.encode()
    )
    first = tns.lookup_objects(["2026yly"], cache_dir=tmp_path)
    a_year_later = datetime.now(UTC) + timedelta(days=365)
    second = tns.lookup_objects(["2026yly"], now=a_year_later, cache_dir=tmp_path)
    assert first["2026yly"] == second["2026yly"]
    assert len(calls) == 1


def test_lookup_objects_retries_an_unknown_name_only_after_a_day(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []
    monkeypatch.setattr(
        _http, "get", lambda url, source: calls.append(url) or TNS_HEADER.encode()
    )
    now = datetime.now(UTC)
    assert tns.lookup_objects(["2099zzz"], now=now, cache_dir=tmp_path) == {}
    tns.lookup_objects(["2099zzz"], now=now + timedelta(hours=2), cache_dir=tmp_path)
    tns.lookup_objects(["2099zzz"], now=now + timedelta(hours=25), cache_dir=tmp_path)
    assert len(calls) == 2


def test_lookup_objects_caps_requests_per_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []
    monkeypatch.setattr(
        _http, "get", lambda url, source: calls.append(url) or TNS_HEADER.encode()
    )
    tns.lookup_objects([f"2026a{i:03d}" for i in range(20)], cache_dir=tmp_path)
    assert len(calls) == tns.MAX_LOOKUPS_PER_RUN


def test_a_429_holds_tns_off_for_exactly_the_servers_reset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []

    def rate_limited(url, source):
        calls.append(url)
        raise EventsUnavailable("429", retry_after=timedelta(seconds=27))

    monkeypatch.setattr(_http, "get", rate_limited)
    now = datetime.now(UTC)
    tns.lookup_objects(["2026a", "2026b", "2026c"], now=now, cache_dir=tmp_path)
    assert len(calls) == 1  # stopped after the first 429
    marker = tmp_path / "tns_objects.json.failed"
    held_until = datetime.fromisoformat(marker.read_text())
    assert held_until - now == timedelta(seconds=27)
    assert _backoff.recently_failed(tmp_path / "tns_objects.json", now)
    assert not _backoff.recently_failed(
        tmp_path / "tns_objects.json", now + timedelta(seconds=28)
    )


def test_http_reads_the_rate_limit_reset_from_a_429() -> None:
    headers = Message()
    headers["x-rate-limit-reset"] = "27"
    error = urllib.error.HTTPError("https://x", 429, "Too Many Requests", headers, None)
    assert _http._retry_after(error) == timedelta(seconds=27)
    other = urllib.error.HTTPError("https://x", 500, "Server Error", Message(), None)
    assert _http._retry_after(other) is None


def test_fetch_recent_novae_queries_once_a_day(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []
    monkeypatch.setattr(
        _http, "get", lambda url, source: calls.append(url) or NOVAE_CSV.encode()
    )
    now = datetime.now(UTC)
    first = tns.fetch_recent_novae(now=now, cache_dir=tmp_path)
    tns.fetch_recent_novae(now=now + timedelta(hours=5), cache_dir=tmp_path)
    assert [n.name for n in first.novae] == ["AT 2026abbx", "AT 2026aaom"]
    assert len(calls) == 1
    assert "objtype%5B%5D=26" in calls[0] and "discovered_period_value=60" in calls[0]


# --- planning ----------------------------------------------------------------


@pytest.fixture
def transient_sources(
    monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> list[list[str]]:
    """Comets as in test_current_events, plus Rochester's table and TNS
    (novae; per-name lookups answer for 2026yly only). Returns the list
    of names TNS was asked to look up."""
    request.getfixturevalue("live_sources")
    fetched = datetime(2026, 10, 4, 9, 0, tzinfo=UTC)
    monkeypatch.setattr(
        rochester,
        "fetch_transient_brightness",
        lambda: rochester.TransientBrightnessReport(
            rochester.parse_latest_supernovae(ROCHESTER_PAGE), fetched
        ),
    )
    monkeypatch.setattr(
        tns,
        "fetch_recent_novae",
        lambda: tns.NovaReport(tns.parse_search_csv(NOVAE_CSV), fetched),
    )
    asked: list[list[str]] = []

    def lookup(names):
        asked.append(list(names))
        return {
            r.objname: r for r in tns.parse_search_csv(YLY_CSV) if r.objname in names
        }

    monkeypatch.setattr(tns, "lookup_objects", lookup)
    return asked


def test_supernovae_are_ranked_from_rochester_positions(transient_sources) -> None:
    report = planning.current_events(SITE, SEESTAR, WHEN)
    by_name = {e.target.name: e for e in report.events}

    aaiv = by_name["SN 2026aaiv"]
    assert aaiv.kind == "supernova"
    assert aaiv.target.types == ("supernova",)
    assert aaiv.target.magnitude == 13.0
    assert aaiv.motion_deg_per_hour is None
    assert aaiv.magnitude_source == "Rochester list 2026-10-04; SN Ia in NGC 7331"
    # Only the entry without a linked position went to TNS.
    assert transient_sources == [["2026yly"]]
    assert "SN 2026yly" in {e.target.name for e in report.events} | {
        s.name for s in report.skipped
    }


def test_transients_left_out_say_why(transient_sources) -> None:
    report = planning.current_events(SITE, SEESTAR, WHEN)
    reasons = {s.name: s.reason for s in report.skipped}

    assert "unclassified transient" in reasons["AT 2026zsr"]
    assert "over a month old" in reasons["SN 2026pub"]
    assert "too faint" in reasons["AT 2026aaom"]  # 15.3 > Seestar limit 15.0
    assert "discovered 2026-09-08 at 12.6 mag" in reasons["AT 2026abbx"]
    # A nova already on Rochester's list isn't repeated as "no brightness".
    assert sum(1 for s in report.skipped if s.name == "AT 2026aaom") == 1


def test_find_event_takes_a_bare_tns_name(transient_sources) -> None:
    report = planning.current_events(SITE, SEESTAR, WHEN)
    event = planning.find_event(report, "2026aaiv")
    assert isinstance(event, planning.RankedEvent)
    assert event.target.name == "SN 2026aaiv"

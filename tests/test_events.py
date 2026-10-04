"""Current-events clients (nachtlotse/events/) — network always mocked;
the suite stays offline (see CLAUDE.md's guiding principle).

The CometEls.txt lines below are verbatim from the MPC's file as
published on 2026-10-04.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nachtlotse.events import EventsUnavailable, _http, cobs, mpc

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)

COMET_ELS = (
    "    CK24J030  2026 11 25.4268  3.865524  0.999946   74.0905  285.9594   75.6391  20261003   8.6  4.0  C/2024 J3 (ATLAS)                                        MPC xxxxx\n"
    "0010P         2026 08  2.1040  1.417739  0.537442  195.4604  117.7968   12.0271  20261003  13.1  4.0  10P/Tempel                                               MPC xxxxx\n"
    "0073P         2027 12 23.1349  0.915713  0.700819  214.6072   52.3008    6.2189  20261003  11.5  6.0  73P/Schwassmann-Wachmann                                 MPC191599\n"
    "0073P     bt  2027 12 25.0541  0.915551  0.701012  214.4738   52.3695    6.1808  20261003  11.5  6.0  73P-BT/Schwassmann-Wachmann                              MPC106348\n"
    "garbage line that is long enough to be considered but has no numbers in it at all ......................................\n"
)


def _observation(key, name, date, magnitude, coma=None, component=None):
    return {
        "obs_date": date,
        "magnitude": magnitude,
        "coma_diameter": coma,
        "comet": {"mpc_name": key, "fullname": name, "component": component},
    }


OBSERVATIONS = [
    _observation("10P", "10P/Tempel", "2026-10-03 12:51:18", "9.0", "6.0"),
    _observation("10P", "10P/Tempel", "2026-10-02 20:00:00", "10.2", None),
    _observation("10P", "10P/Tempel", "2026-10-01 20:00:00", "9.8", "5.0"),
    _observation("K24J030", "C/2024 J3 (ATLAS)", "2026-10-03 21:07:11", "14.1"),
    _observation("K24J030", "C/2024 J3 (ATLAS)", "2026-10-03 22:00:00", None),
    _observation(
        "73P", "73P/Schwassmann-Wachmann", "2026-10-03 01:00:00", "12.0", component="B"
    ),
]


def _page(objects, page, pages) -> bytes:
    return json.dumps(
        {"info": {"page": page, "pages": pages}, "objects": objects}
    ).encode()


# --- shared HTTP seam -------------------------------------------------------


def test_http_get_turns_network_errors_into_events_unavailable() -> None:
    with (
        patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")),
        pytest.raises(EventsUnavailable, match="COBS request failed"),
    ):
        _http.get("https://example.invalid", source="COBS")


def test_http_get_identifies_itself() -> None:
    response = MagicMock()
    response.read.return_value = b"ok"
    response.__enter__.return_value = response
    with patch("urllib.request.urlopen", return_value=response) as urlopen:
        assert _http.get("https://example.invalid", source="x") == b"ok"
    request = urlopen.call_args.args[0]
    assert "Nachtlotse" in request.get_header("User-agent")


# --- MPC comet elements -------------------------------------------------------


def test_parse_comet_elements_reads_every_valid_line() -> None:
    orbits = mpc.parse_comet_elements(COMET_ELS)

    assert set(orbits) == {"K24J030", "10P", "73P", "73P-BT"}
    tempel = orbits["10P"]
    assert tempel.designation == "10P/Tempel"
    assert (tempel.perihelion_year, tempel.perihelion_month) == (2026, 8)
    assert tempel.perihelion_day == pytest.approx(2.1040)
    assert tempel.perihelion_distance_au == pytest.approx(1.417739)
    assert tempel.eccentricity == pytest.approx(0.537442)
    assert tempel.argument_of_perihelion_deg == pytest.approx(195.4604)
    assert tempel.longitude_of_ascending_node_deg == pytest.approx(117.7968)
    assert tempel.inclination_deg == pytest.approx(12.0271)


def test_a_fragment_doesnt_overwrite_its_parent_comet() -> None:
    orbits = mpc.parse_comet_elements(COMET_ELS)
    assert orbits["73P"].designation == "73P/Schwassmann-Wachmann"
    assert orbits["73P-BT"].designation == "73P-BT/Schwassmann-Wachmann"


def test_fetch_comet_orbits_downloads_then_serves_the_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []
    monkeypatch.setattr(
        _http, "get", lambda url, source: calls.append(url) or COMET_ELS.encode()
    )
    first = mpc.fetch_comet_orbits(now=datetime.now(UTC), cache_dir=tmp_path)
    second = mpc.fetch_comet_orbits(now=datetime.now(UTC), cache_dir=tmp_path)

    assert calls == [mpc.COMET_ELEMENTS_URL]
    assert (
        set(first.orbits) == set(second.orbits) == {"K24J030", "10P", "73P", "73P-BT"}
    )


def _age_cache(path: Path, hours: float) -> None:
    old = datetime.now(UTC) - timedelta(hours=hours)
    os.utime(path, (old.timestamp(), old.timestamp()))


def test_fetch_comet_orbits_falls_back_to_a_stale_cache_when_offline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(_http, "get", lambda url, source: COMET_ELS.encode())
    mpc.fetch_comet_orbits(cache_dir=tmp_path)
    _age_cache(tmp_path / "CometEls.txt", hours=72)

    def offline(url, source):
        raise EventsUnavailable("offline")

    monkeypatch.setattr(_http, "get", offline)
    stale = mpc.fetch_comet_orbits(cache_dir=tmp_path)
    assert "10P" in stale.orbits
    assert datetime.now(UTC) - stale.fetched_at > timedelta(hours=71)


def test_fetch_comet_orbits_raises_offline_without_a_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def offline(url, source):
        raise EventsUnavailable("offline")

    monkeypatch.setattr(_http, "get", offline)
    with pytest.raises(EventsUnavailable):
        mpc.fetch_comet_orbits(cache_dir=tmp_path)


def test_fetch_comet_orbits_rejects_and_doesnt_cache_an_unparsable_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(_http, "get", lambda url, source: b"<html>maintenance</html>")
    with pytest.raises(EventsUnavailable, match="no parsable orbits"):
        mpc.fetch_comet_orbits(cache_dir=tmp_path)
    assert not (tmp_path / "CometEls.txt").exists()


# --- COBS observed brightness -------------------------------------------------


def test_summarize_observations_takes_medians_per_comet() -> None:
    summary = cobs.summarize_observations(OBSERVATIONS)

    # Fragments (component) and reports without a magnitude are skipped.
    assert set(summary) == {"10P", "K24J030"}
    tempel = summary["10P"]
    assert tempel.designation == "10P/Tempel"
    assert tempel.magnitude == pytest.approx(9.8)  # median of 9.0, 10.2, 9.8
    assert tempel.report_count == 3
    assert tempel.last_reported == datetime(2026, 10, 3, 12, 51, 18, tzinfo=UTC)
    assert tempel.coma_diameter_arcmin == pytest.approx(5.5)  # median of 6.0, 5.0
    atlas = summary["K24J030"]
    assert (atlas.magnitude, atlas.report_count) == (14.1, 1)
    assert atlas.coma_diameter_arcmin is None


def test_fetch_comet_brightness_pages_through_the_last_two_weeks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    urls = []

    def fake_get(url, source):
        urls.append(url)
        page = int(urllib.parse.parse_qs(urllib.parse.urlparse(url).query)["page"][0])
        return _page(OBSERVATIONS[:3] if page == 1 else OBSERVATIONS[3:], page, 2)

    monkeypatch.setattr(_http, "get", fake_get)
    report = cobs.fetch_comet_brightness(now=NOW, cache_dir=tmp_path)

    assert len(urls) == 2
    query = urllib.parse.parse_qs(urllib.parse.urlparse(urls[0]).query)
    assert query["from_date"] == ["2026-09-20"]  # NOW - 14 days
    assert query["format"] == ["json"]
    assert set(report.comets) == {"10P", "K24J030"}
    assert report.window_days == cobs.WINDOW_DAYS


def test_fetch_comet_brightness_serves_fresh_then_stale_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(_http, "get", lambda url, source: _page(OBSERVATIONS, 1, 1))
    cobs.fetch_comet_brightness(now=NOW, cache_dir=tmp_path)

    def offline(url, source):
        raise EventsUnavailable("offline")

    monkeypatch.setattr(_http, "get", offline)
    fresh = cobs.fetch_comet_brightness(
        now=NOW + timedelta(hours=1), cache_dir=tmp_path
    )
    stale = cobs.fetch_comet_brightness(now=NOW + timedelta(days=3), cache_dir=tmp_path)
    assert fresh.fetched_at == stale.fetched_at == NOW
    assert stale.comets["10P"].magnitude == pytest.approx(9.8)


def test_fetch_comet_brightness_raises_on_garbage_without_a_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(_http, "get", lambda url, source: b"not json")
    with pytest.raises(EventsUnavailable, match="malformed"):
        cobs.fetch_comet_brightness(now=NOW, cache_dir=tmp_path)

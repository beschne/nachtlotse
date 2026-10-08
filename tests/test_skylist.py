"""Tests for the SkySafari `.skylist` export (nachtlotse/skylist.py).

`fixtures/skysafari_reference.skylist` is a list SkySafari 6 itself
exported (M31, M42, comets 220P and C/2014 UN271); the format code is
checked against it rather than against remembered format details.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from nachtlotse import cli, planning, skylist
from nachtlotse.engine import ephemeris
from nachtlotse.engine.models import Target, Verdict

REFERENCE = Path(__file__).parent / "fixtures" / "skysafari_reference.skylist"

_NOW = datetime(2026, 10, 8, 22, 0, tzinfo=UTC)
_POS = ephemeris.AltAz(alt_deg=45.0, az_deg=180.0, distance_au=0.0)

M31 = Target(
    name="Andromeda Galaxy",
    catalog_id="M31",
    aliases=("NGC 224",),
    ra_deg=10.6847,
    dec_deg=41.2692,
    types=("galaxy",),
)
M42 = Target(
    name="Orion Nebula",
    catalog_id="M42",
    aliases=("NGC 1976",),
    ra_deg=83.85,
    dec_deg=-5.45,
    types=("emission_nebula",),
)
M81 = Target(name="Bode's Galaxy", catalog_id="M81", ra_deg=148.9, dec_deg=69.07)
M82 = Target(name="Cigar Galaxy", catalog_id="M82", ra_deg=148.97, dec_deg=69.68)


def _parse(text: str) -> list[dict[str, list[str]]]:
    """Blocks of a skylist as {key: [values]} dicts, header excluded."""
    blocks: list[dict[str, list[str]]] = []
    current: dict[str, list[str]] | None = None
    for line in text.splitlines():
        if line == "SkyObject=BeginObject":
            current = {}
        elif line == "EndObject=SkyObject":
            assert current is not None
            blocks.append(current)
            current = None
        elif current is not None:
            key, _, value = line.strip().partition("=")
            current.setdefault(key, []).append(value)
    return blocks


def _ranked(target: Target) -> planning.RankedTarget:
    return planning.RankedTarget(target, _NOW, _POS, fit=1.0, reach=1.0)


def _event(kind: str, target: Target) -> planning.RankedEvent:
    return planning.RankedEvent(
        kind,  # type: ignore[arg-type]
        target,
        _NOW,
        _POS,
        1.0,
        1.0,
        Verdict("GO", []),
        "test",
        None,
    )


def _plan(
    shortlist: list[planning.RankedEntry],
    ranked: list[planning.RankedEntry],
    events: list[planning.RankedEvent],
) -> planning.NightPlan:
    return planning.NightPlan(
        site=None,  # type: ignore[arg-type]
        rig=None,  # type: ignore[arg-type]
        evening_start=_NOW,
        morning_end=_NOW,
        moon_illumination_pct=0.0,
        moonrise=None,
        moonset=None,
        weather=None,
        hourly_cloud_cover=[],
        ranked=ranked,
        shortlist=[
            planning.ShortlistEntry(entry, Verdict("GO", [])) for entry in shortlist
        ],
        events=planning.EventsReport(events, [], []),
    )


def test_header_matches_the_skysafari_reference() -> None:
    reference = REFERENCE.read_text().splitlines()
    assert skylist.skylist_text([]).splitlines() == reference[:2]


def test_catalog_entries_carry_the_reference_names_and_catalog_numbers() -> None:
    reference = {
        block["CommonName"][0]: block for block in _parse(REFERENCE.read_text())
    }
    for target in (M31, M42):
        (block,) = _parse(skylist.skylist_text([skylist.catalog_entry(target)]))
        expected = reference[target.name]
        assert block["CommonName"] == expected["CommonName"]
        # SkySafari lists more catalogs (UGC, PGC, ...) than the catalog has.
        assert (
            block["CatalogNumber"]
            == expected["CatalogNumber"][: len(block["CatalogNumber"])]
        )
        assert "ObjectID" not in block


def test_messier_ids_get_skysafaris_space_and_other_designations_stay() -> None:
    assert skylist.skysafari_catalog_number("M31") == "M 31"
    assert skylist.skysafari_catalog_number("M110") == "M 110"
    assert skylist.skysafari_catalog_number("NGC 224") == "NGC 224"
    assert skylist.skysafari_catalog_number("IC 1396") == "IC 1396"


def test_comet_entries_carry_the_reference_names_and_a_comet_type_id() -> None:
    (reference,) = [
        block
        for block in _parse(REFERENCE.read_text())
        if block.get("ObjectID", [""])[0].startswith("1,0,")
        and "220P" in block["CommonName"]
    ]
    periodic = Target(name="220P/McNaught", ra_deg=0.0, dec_deg=0.0, types=("comet",))
    (block,) = _parse(skylist.skylist_text([skylist.comet_entry(periodic, 0)]))
    assert set(block["CommonName"]) == set(reference["CommonName"])
    assert block["ObjectID"][0].startswith("1,0,")


def test_comet_names_drop_the_parenthesised_name_into_a_second_entry() -> None:
    names = skylist._comet_names("C/2014 UN271 (Bernardinelli-Bernstein)")
    assert names == (
        "C/2014 UN271 (Bernardinelli-Bernstein)",
        "C/2014 UN271",
    )
    assert skylist._comet_names("C/2026 A2") == ("C/2026 A2",)


def test_comet_placeholder_ids_are_unique_per_comet() -> None:
    first = skylist.comet_entry(Target("C/2026 A2", 0.0, 0.0), 0)
    second = skylist.comet_entry(Target("C/2026 B1", 0.0, 0.0), 1)
    assert first.object_id != second.object_id


@pytest.mark.parametrize(
    ("ra_deg", "dec_deg", "expected"),
    [
        (188.5, -12.5, "RA 12h34m Dec -12d30m J2000"),
        (0.0, 0.0, "RA 00h00m Dec +00d00m J2000"),
        (359.99, 89.99, "RA 00h00m Dec +89d59m J2000"),
    ],
)
def test_transients_are_name_only_with_coordinates_in_the_name(
    ra_deg: float, dec_deg: float, expected: str
) -> None:
    target = Target(
        name="SN 2026xyz", ra_deg=ra_deg, dec_deg=dec_deg, types=("supernova",)
    )
    entry = skylist.transient_entry(target)
    assert entry.common_names == (f"SN 2026xyz ({expected})",)
    assert entry.catalog_numbers == ()
    assert entry.object_id is None


def test_default_index_counts_up_from_zero() -> None:
    entries = [skylist.catalog_entry(M31), skylist.catalog_entry(M42)]
    blocks = _parse(skylist.skylist_text(entries))
    assert [b["DefaultIndex"] for b in blocks] == [["0"], ["1"]]


def test_plan_entries_are_the_shortlist_then_comets_then_transients() -> None:
    comet = Target("C/2026 A2", 10.0, 10.0, types=("comet",))
    supernova = Target("SN 2026xyz", 20.0, 20.0, types=("supernova",))
    plan = _plan(
        shortlist=[_ranked(M31)],
        ranked=[_ranked(M31), _ranked(M42)],
        events=[_event("supernova", supernova), _event("comet", comet)],
    )
    names = [e.common_names[0] for e in skylist.entries_for_plan(plan)]
    assert names[:2] == ["Andromeda Galaxy", "C/2026 A2"]
    assert names[2].startswith("SN 2026xyz (RA ")
    assert len(names) == 3


def test_ranked_scope_writes_the_whole_ranking() -> None:
    plan = _plan(
        shortlist=[_ranked(M31)],
        ranked=[_ranked(M31), _ranked(M42)],
        events=[],
    )
    names = [e.common_names[0] for e in skylist.entries_for_plan(plan, "ranked")]
    assert names == ["Andromeda Galaxy", "Orion Nebula"]


def test_groups_expand_to_their_members_and_duplicates_are_listed_once() -> None:
    group = planning.RankedGroup((M81, M82), _NOW, _POS, 1.0, 1.0)
    plan = _plan(shortlist=[group, _ranked(M81)], ranked=[group], events=[])
    names = [e.common_names[0] for e in skylist.entries_for_plan(plan)]
    assert names == ["Bode's Galaxy", "Cigar Galaxy"]


def test_plan_without_events_report_writes_only_targets() -> None:
    plan = _plan(shortlist=[_ranked(M31)], ranked=[_ranked(M31)], events=[])
    plan = planning.NightPlan(**{**plan.__dict__, "events": None})
    assert len(skylist.entries_for_plan(plan)) == 1


def test_plan_command_writes_a_skylist(
    template_sites, template_rigs, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "tonight.skylist"
    exit_code = cli.main(["plan", "--no-events", "--skylist", str(path)])
    assert exit_code == 0
    assert f"SkySafari list written to {path}" in capsys.readouterr().out
    text = path.read_text()
    assert text.startswith("SkySafariObservingListVersion=3.0\n")
    assert text.count("SkyObject=BeginObject") >= 1


def test_plan_command_reports_an_unwritable_skylist_path(
    template_sites, template_rigs, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = cli.main(
        ["plan", "--no-events", "--skylist", str(tmp_path / "missing" / "x.skylist")]
    )
    assert exit_code == 2
    assert "Couldn't write" in capsys.readouterr().err


def test_skylist_cannot_be_combined_with_best_rig(
    template_sites, template_rigs, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = cli.main(
        ["plan", "--best-rig", "--skylist", str(tmp_path / "x.skylist")]
    )
    assert exit_code == 2
    assert "--skylist" in capsys.readouterr().err

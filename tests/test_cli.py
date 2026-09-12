from __future__ import annotations

import pytest

from nachtlotse import cli


def test_today_command_prints_a_ranking_sorted_by_descending_altitude(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["today"])
    assert exit_code == 0

    output = capsys.readouterr().out
    assert cli.BAD_HOMBURG.name in output
    assert cli.SEESTAR_S30_PRO.name in output

    lines = [line for line in output.splitlines()[2:] if line.strip()]
    assert lines, "expected at least one ranked target line"


def test_rank_targets_is_sorted_by_descending_transit_altitude() -> None:
    from datetime import UTC, datetime

    ranked = cli._rank_targets(cli.BAD_HOMBURG, datetime.now(UTC))
    altitudes = [pos.alt_deg for _target, _transit_time, pos in ranked]

    assert altitudes == sorted(altitudes, reverse=True)
    assert all(alt_deg > 0.0 for alt_deg in altitudes)


def test_unknown_command_is_rejected() -> None:
    with pytest.raises(SystemExit):
        cli.main(["nonsense"])

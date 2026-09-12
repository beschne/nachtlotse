from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nachtlotse import cli


def test_today_command_prints_dark_window_moon_and_a_ranked_table(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(["today"])
    assert exit_code == 0

    output = capsys.readouterr().out
    assert cli.BAD_HOMBURG.name in output
    assert cli.SEESTAR_S30_PRO.name in output
    assert "Dark window:" in output
    assert "Moon:" in output

    ranked = cli._rank_targets(cli.BAD_HOMBURG, datetime.now(UTC))
    for target, *_rest in ranked:
        assert target.catalog_id in output


def test_rank_targets_is_sorted_by_descending_altitude_and_passes_constraints() -> None:
    ranked = cli._rank_targets(cli.BAD_HOMBURG, datetime.now(UTC))
    altitudes = [pos.alt_deg for _target, _max_time, pos in ranked]

    assert altitudes == sorted(altitudes, reverse=True)
    assert all(alt_deg > 0.0 for alt_deg in altitudes)
    assert all(
        cli.constraints.is_observable_tonight(
            cli.BAD_HOMBURG, target, datetime.now(UTC)
        )
        for target, _max_time, _pos in ranked
    )


def test_unknown_command_is_rejected() -> None:
    with pytest.raises(SystemExit):
        cli.main(["nonsense"])

"""Regenerates every "Export from the GUI" output for tonight's default
site/rig, without opening the GUI — calling the exact same functions
each screen's own "Export …" button calls (`nachtlotse.gui.export`,
`nachtlotse.chart_export`, `nachtlotse.prose`), writing into this same
`exports/` directory (`nachtlotse.gui.export.default_export_dir`).

The briefing needs the Anthropic API (`prose.generate_nightly_briefing`)
— same as the GUI's own "Generate briefing" button and the CLI's
`--prose` flag, it's skipped rather than failing the whole run when
`ANTHROPIC_API_KEY`/`prose_local.yaml` isn't configured.

Run from the repo root: `uv run python exports/generate_exports.py`
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from nachtlotse import chart_export, planning, prose
from nachtlotse.data import store
from nachtlotse.gui import data_adapter
from nachtlotse.gui import export as gui_export


def main() -> None:
    site = store.default_site_record().site
    rig = store.default_rig_record().rig
    plan = planning.plan_night(site, rig, datetime.now(UTC))
    local_tz = ZoneInfo(site.tz)
    out_dir = gui_export.default_export_dir()

    shortlist_rows = data_adapter.build_shortlist_rows(plan, local_tz)
    ranked_rows = data_adapter.build_ranked_rows(plan, local_tz)

    gui_export.write_text(
        gui_export.shortlist_csv_text(shortlist_rows),
        out_dir / gui_export.DEFAULT_SHORTLIST_CSV_FILENAME,
    )
    gui_export.write_text(
        gui_export.ranked_csv_text(ranked_rows),
        out_dir / gui_export.DEFAULT_RANKED_CSV_FILENAME,
    )
    gui_export.write_text(
        gui_export.sites_text(store.SITES),
        out_dir / gui_export.DEFAULT_SITES_TXT_FILENAME,
    )
    gui_export.write_text(
        gui_export.rigs_text(store.RIGS), out_dir / gui_export.DEFAULT_RIGS_TXT_FILENAME
    )
    print(f"wrote {gui_export.DEFAULT_SHORTLIST_CSV_FILENAME}")
    print(f"wrote {gui_export.DEFAULT_RANKED_CSV_FILENAME}")
    print(f"wrote {gui_export.DEFAULT_SITES_TXT_FILENAME}")
    print(f"wrote {gui_export.DEFAULT_RIGS_TXT_FILENAME}")

    try:
        chart_export.save_shortlist_chart(
            plan, out_dir / chart_export.DEFAULT_CHART_FILENAME
        )
        print(f"wrote {chart_export.DEFAULT_CHART_FILENAME}")
    except (chart_export.ChartExportUnavailable, ValueError) as exc:
        print(f"skipped {chart_export.DEFAULT_CHART_FILENAME}: {exc}")

    try:
        briefing_text = prose.generate_nightly_briefing(plan)
    except prose.ProseUnavailable as exc:
        print(f"skipped {gui_export.DEFAULT_BRIEFING_TXT_FILENAME}: {exc}")
    else:
        gui_export.write_text(
            briefing_text, out_dir / gui_export.DEFAULT_BRIEFING_TXT_FILENAME
        )
        print(f"wrote {gui_export.DEFAULT_BRIEFING_TXT_FILENAME}")


if __name__ == "__main__":
    main()

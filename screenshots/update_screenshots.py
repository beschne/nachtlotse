"""Regenerates the GUI screenshots in this directory.

Drives the real `MainWindow` in-process against real data (no
illustrative/fake data, same rule the GUI itself follows) for a fixed
site/rig/date, then screencaptures the Shortlist, Sky chart, and Best
sky tabs — switching tabs via `QTabWidget.setCurrentIndex()` directly,
not by simulating a mouse click on the tab bar. Clicking required
finding the window on screen and hoping the coordinates still matched
after any resize/reposition; this doesn't, since the script already
holds the `MainWindow` object it's capturing.

Only `gui-shortlist.png` and `gui-sky-chart.png` are embedded in
README.md; `gui-best-sky.png` is kept here for reference only (not
embedded anywhere) — still regenerated alongside the other two so it
doesn't go stale unnoticed.

Needs `screencapture` (macOS, always present) and `pyobjc-framework-
Quartz` (to look up the window's CGWindowID — not part of the `gui`
extra, since nothing else in the app needs it) and `sips` (macOS,
always present) for the final resize. Run with:

    uv run --extra gui --with pyobjc-framework-Quartz \
        python3 screenshots/update_screenshots.py

Edit SITE_NAME / RIG_NAME / TARGET_DATE below for a different
combination — and update the caption in README.md's "Native GUI"
section to match; this script doesn't touch that text.
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication

from nachtlotse.gui.best_sky_card import BestSkyCard
from nachtlotse.gui.main_window import MainWindow

SITE_NAME = "Volkssternwarte Hochtaunus"
RIG_NAME = "TEC AP 160/1120 f/7 FL"
TARGET_DATE = date(2026, 9, 25)

# Best Sky doesn't use rig data at all (it's a weather-only comparison),
# so this only changes what the header above the tabs shows while it's
# captured — the project's actual reference-case rig (CLAUDE.md: "First
# rig (reference case)"), alt-az specifically, rather than RIG_NAME's
# exotic APO refractor.
BEST_SKY_RIG_NAME = "ZWO Seestar S30 Pro"

SCREENSHOTS_DIR = Path(__file__).resolve().parent
RESIZE_WIDTH = 1600
# Taller than MainWindow's own default (1300x700) so the Best Sky
# capture below shows every configured site's row without a scrollbar
# cutting the list off.
WINDOW_SIZE = (1300, 1150)

# (tab index, output filename) — see main_window.py's own addTab() order.
SHORTLIST_TAB_INDEX = 0
SKY_CHART_TAB_INDEX = 2
BEST_SKY_TAB_INDEX = 4


def _pump(app: QApplication, worker_holder: MainWindow | BestSkyCard, seconds: float) -> None:
    """Works for anything holding a `._worker` QThread — `MainWindow`
    itself (the plan worker) or `BestSkyCard` (its own refresh worker)."""
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        if worker_holder._worker is None or not worker_holder._worker.isRunning():
            break
        time.sleep(0.05)
    for _ in range(20):
        app.processEvents()
        time.sleep(0.02)


def _find_window_id(title: str) -> int:
    import Quartz

    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID
    )
    for w in windows:
        if w.get("kCGWindowOwnerName", "") == "python3" and w.get("kCGWindowName") == title:
            return w.get("kCGWindowNumber")
    raise RuntimeError(f"Could not find an on-screen window titled {title!r}")


def _capture(window_id: int, out_path: Path) -> None:
    subprocess.run(["screencapture", "-l", str(window_id), "-x", str(out_path)], check=True)
    subprocess.run(["sips", "-Z", str(RESIZE_WIDTH), str(out_path)], check=True, capture_output=True)


def _switch_tab(app: QApplication, window: MainWindow, tab_index: int) -> None:
    """`setCurrentIndex()` alone doesn't guarantee the new tab has
    actually repainted by the time this returns — same lesson as
    populating a table earlier in this project's own history: Qt/macOS
    needs several event-loop turns, not just one, before a screencapture
    of the result is trustworthy."""
    window.tabs.setCurrentIndex(tab_index)
    for _ in range(20):
        app.processEvents()
        time.sleep(0.02)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()  # MainWindow's own default size (1300x700)
    window.show()
    app.processEvents()
    _pump(app, window, 20.0)  # the initial (today's) plan on construction

    sidebar = window.sidebar
    try:
        site_record = next(r for r in sidebar._sites if r.site.name == SITE_NAME)
        rig_record = next(r for r in sidebar._rigs if r.rig.name == RIG_NAME)
        best_sky_rig_record = next(
            r for r in sidebar._rigs if r.rig.name == BEST_SKY_RIG_NAME
        )
    except StopIteration as exc:
        print(f"Site or rig not found in your local config: {exc}", file=sys.stderr)
        return 2

    # Keep the sidebar widgets themselves in sync — _replan() alone updates
    # the content, not the combo boxes/date picker, which would otherwise
    # keep showing whatever was selected when the window was constructed.
    sidebar.site_combo.setCurrentIndex(sidebar._sites.index(site_record))
    sidebar.rig_combo.setCurrentIndex(sidebar._rigs.index(rig_record))
    sidebar.date_edit.setDate(QDate(TARGET_DATE.year, TARGET_DATE.month, TARGET_DATE.day))
    sidebar.replan_button.setEnabled(False)

    window._replan(site_record, rig_record, TARGET_DATE, sidebar.current_limit())
    _pump(app, window, 20.0)

    window_id = _find_window_id(window.windowTitle())

    _switch_tab(app, window, SHORTLIST_TAB_INDEX)
    _capture(window_id, SCREENSHOTS_DIR / "gui-shortlist.png")

    _switch_tab(app, window, SKY_CHART_TAB_INDEX)
    _capture(window_id, SCREENSHOTS_DIR / "gui-sky-chart.png")

    # Re-plan with the alt-az Seestar before the Best Sky capture, purely
    # so its header above the tabs reflects that rig — Best Sky itself
    # doesn't use rig data at all (see BEST_SKY_RIG_NAME above).
    sidebar.rig_combo.setCurrentIndex(sidebar._rigs.index(best_sky_rig_record))
    sidebar.replan_button.setEnabled(False)
    window._replan(site_record, best_sky_rig_record, TARGET_DATE, sidebar.current_limit())
    _pump(app, window, 20.0)

    # Taller than the default for this capture only, so the full site
    # list shows without a scrollbar cutting it off — Shortlist/Sky
    # chart above were already captured at the default size.
    window.resize(*WINDOW_SIZE)
    for _ in range(20):
        app.processEvents()
        time.sleep(0.02)

    _switch_tab(app, window, BEST_SKY_TAB_INDEX)
    window.best_sky.set_center(site_record)  # match the rest of this screenshot's site
    window.best_sky.refresh_button.click()
    _pump(app, window.best_sky, 30.0)  # a real per-site Open-Meteo fetch, not instant
    _capture(window_id, SCREENSHOTS_DIR / "gui-best-sky.png")

    window.close()
    print("Wrote gui-shortlist.png, gui-sky-chart.png, and gui-best-sky.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

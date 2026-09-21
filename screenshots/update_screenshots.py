"""Regenerates the two GUI screenshots embedded in README.md.

Drives the real `MainWindow` in-process against real data (no
illustrative/fake data, same rule the GUI itself follows) for a fixed
site/rig/date, then screencaptures the Shortlist and Sky chart tabs —
switching tabs via `QTabWidget.setCurrentIndex()` directly, not by
simulating a mouse click on the tab bar. Clicking required finding the
window on screen and hoping the coordinates still matched after any
resize/reposition; this doesn't, since the script already holds the
`MainWindow` object it's capturing.

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

from nachtlotse.gui.main_window import MainWindow

SITE_NAME = "Volkssternwarte Hochtaunus"
RIG_NAME = "TEC AP 160/1120 f/7 FL"
TARGET_DATE = date(2026, 9, 25)

SCREENSHOTS_DIR = Path(__file__).resolve().parent
RESIZE_WIDTH = 1600

# (tab index, output filename) — see main_window.py's own addTab() order.
SHORTLIST_TAB_INDEX = 0
SKY_CHART_TAB_INDEX = 2


def _pump(app: QApplication, worker_holder: MainWindow, seconds: float) -> None:
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
    window = MainWindow()
    window.show()
    app.processEvents()
    _pump(app, window, 20.0)  # the initial (today's) plan on construction

    sidebar = window.sidebar
    try:
        site_record = next(r for r in sidebar._sites if r.site.name == SITE_NAME)
        rig_record = next(r for r in sidebar._rigs if r.rig.name == RIG_NAME)
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

    window._replan(site_record, rig_record, TARGET_DATE)
    _pump(app, window, 20.0)

    window_id = _find_window_id(window.windowTitle())

    _switch_tab(app, window, SHORTLIST_TAB_INDEX)
    _capture(window_id, SCREENSHOTS_DIR / "gui-shortlist.png")

    _switch_tab(app, window, SKY_CHART_TAB_INDEX)
    _capture(window_id, SCREENSHOTS_DIR / "gui-sky-chart.png")

    window.close()
    print("Wrote gui-shortlist.png and gui-sky-chart.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

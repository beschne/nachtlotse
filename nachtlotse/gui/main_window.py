"""The main window: sidebar + tonight's shortlist.

Wires real data end to end — `planning.plan_night` against whichever
site/rig/date is staged in the sidebar. No illustrative sample data
anywhere in this package, unlike the throwaway framework spike that
preceded it (deleted once it had settled the PySide6-vs-PyObjC
decision — see ROADMAP.md).

Every screen from the original scaffolding plan is now here: the
shortlist, the full ranked table, the polar sky chart, the LLM
briefing, and read-only Sites/Rigs reference screens (see
`sites_rigs.py`'s own docstring for why they're read-only, not an editor).

`planning.plan_night` runs on a background `QThread` (`_PlanWorker`),
same reasoning as `briefing._BriefingWorker`: it's not instant (catalog
ephemeris + an Open-Meteo fetch), and running it on the UI thread would
freeze the window for that long — visible only as the OS's own
"app not responding" cursor, not a real progress indicator. An
indeterminate `QProgressBar` plus an explicit wait cursor stand in for
one instead; the sidebar is disabled for the same span so a second
Re-plan can't be staged while one is already in flight.
"""

from __future__ import annotations

from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nachtlotse import planning
from nachtlotse.data import store
from nachtlotse.data.store import RigRecord, SiteRecord
from nachtlotse.engine.models import Rig, Site
from nachtlotse.gui import data_adapter
from nachtlotse.gui import export as gui_export
from nachtlotse.gui.briefing import BriefingCard
from nachtlotse.gui.hourly_cloud_bar import HourlyCloudCoverBar
from nachtlotse.gui.sidebar import Sidebar
from nachtlotse.gui.sites_rigs import RigsCard, SitesCard
from nachtlotse.gui.sky_chart import SkyChartCard
from nachtlotse.gui.theme import (
    COLORS,
    RoundedCard,
    VerdictBadge,
    label_style,
    secondary_button,
)
from nachtlotse.planning import NightPlan

_SHORTLIST_COLUMNS = [
    ("label", "Target", "left"),
    ("type_label", "Type", "left"),
    ("alt_text", "Alt", "right"),
    ("az_text", "Az", "right"),
    ("fit_text", "Fit", "right"),
    ("reach_text", "Reach", "right"),
    ("best_time_text", "Best", "right"),
    ("verdict", "Verdict", "center"),
]

_RANKED_COLUMNS = [
    ("label", "Target", "left"),
    ("type_label", "Type", "left"),
    ("alt_text", "Alt", "right"),
    ("az_text", "Az", "right"),
    ("fit_text", "Fit", "right"),
    ("reach_text", "Reach", "right"),
    ("best_time_text", "Best", "right"),
]

_ALIGN = {"left": Qt.AlignLeft, "right": Qt.AlignRight, "center": Qt.AlignCenter}

# Column headers whose meaning isn't self-evident from a two-line QSS
# header — see `engine.framing.framing_score`/`reach_factor` for the
# real definitions this paraphrases. Qt tooltips don't wrap plain text
# on their own, so line breaks are placed by hand rather than left to
# render as one very long line.
_COLUMN_TOOLTIPS = {
    "alt_text": (
        "Alt — altitude at the target's Best time (this row's\n"
        '"Best" column), not right now or at plan time.'
    ),
    "az_text": (
        "Az — azimuth at the target's Best time (this row's\n"
        '"Best" column), not right now or at plan time.'
    ),
    "fit_text": (
        "Fit — how well the target's angular size fills\n"
        "the rig's field of view (0-1). Low doesn't exclude\n"
        "a target, it just means a small subject in a big frame."
    ),
    "reach_text": (
        "Reach — how reachable the target's surface brightness\n"
        "is against this site's sky darkness (0-1). Fades for a\n"
        "diffuse target under a brighter sky, but never to zero —\n"
        "the surface-brightness estimate is a starting heuristic,\n"
        "not a hard cutoff. 1.0 whenever magnitude, size, or the\n"
        "site's sky brightness isn't known."
    ),
}


def _verdict_column_width() -> int:
    """The Verdict column's fixed width — measured from a throwaway
    `VerdictBadge("MARGINAL")`, the widest of the three verdict words.
    See `_build_table`'s own comment for why this column can't just use
    `ResizeToContents` like the others.

    +16, not a small margin: `QTableWidget::item`'s own QSS `padding:
    6px 8px` (8px each side) gets applied by Qt's internal editor/cell-
    widget geometry pass even though a cell *widget* never paints via
    that stylesheet rule itself — confirmed by measurement, not
    documented behavior. Size the column short of that and the actual
    widget geometry ends up 16px narrower than the column, clipping
    "MARGINAL" to "MARGINA" no matter how wide the column claims to be.
    """
    return VerdictBadge("MARGINAL").sizeHint().width() + 16 + 4


def local_when(selected_date: date, local_tz: ZoneInfo) -> datetime:
    """Noon local time on `selected_date` — unambiguously daytime, so
    `constraints.dark_window` picks the night starting that evening.
    Mirrors `cli.py`'s `_resolve_when`."""
    return datetime.combine(selected_date, time(12, 0), tzinfo=local_tz)


def title_for_date(selected_date: date, local_tz: ZoneInfo) -> str:
    """ "Tonight" for today (in the *site's* timezone, not the machine's
    own) — otherwise the actual date, so planning ahead doesn't keep
    reading "Tonight" for a night that isn't tonight at all."""
    if selected_date == datetime.now(local_tz).date():
        return "Tonight"
    return f"{selected_date:%A, %B %-d}"


class _PlanWorker(QThread):
    """Runs `planning.plan_night` off the UI thread."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, site: Site, rig: Rig, when: datetime, limit: int) -> None:
        super().__init__()
        self._site = site
        self._rig = rig
        self._when = when
        self._limit = limit

    def run(self) -> None:
        try:
            plan = planning.plan_night(self._site, self._rig, self._when, limit=self._limit)
        except Exception as exc:  # noqa: BLE001 — surface any failure to the UI, don't crash it
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(plan)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Nachtlotse")
        self.resize(1300, 700)

        central = QWidget()
        central.setStyleSheet(f"background: {COLORS['cream']};")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(24)

        self.sidebar = Sidebar(store.SITES, store.RIGS)
        self.sidebar.replan_requested.connect(self._replan)
        root.addWidget(self.sidebar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 8, 0, 0)
        content_layout.setSpacing(6)
        root.addWidget(content, stretch=1)

        self.eyebrow = QLabel()
        self.eyebrow.setStyleSheet(
            label_style(
                f"color: {COLORS['clay']}; font-size: 12px; font-weight: 600; letter-spacing: 1px;"
            )
        )
        self.title = QLabel("Tonight")
        self.title.setStyleSheet(
            label_style(f"color: {COLORS['ink']}; font-size: 34px; font-weight: 500;")
        )
        self.sub = QLabel()
        self.sub.setStyleSheet(
            label_style(f"color: {COLORS['ink_secondary']}; font-size: 13px;")
        )
        self.weather_label = QLabel()
        self.weather_label.setStyleSheet(
            label_style(f"color: {COLORS['ink_secondary']}; font-size: 12px;")
        )
        self.hourly_cloud_bar = HourlyCloudCoverBar()

        self.progress = QProgressBar()
        self.progress.setRange(
            0, 0
        )  # indeterminate: we don't know how long a plan will take
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(
            f"""
            QProgressBar {{ background: {COLORS["border"]}; border: none; border-radius: 2px; }}
            QProgressBar::chunk {{ background: {COLORS["clay"]}; border-radius: 2px; }}
            """
        )
        self.progress.hide()

        content_layout.addWidget(self.eyebrow)
        content_layout.addWidget(self.title)
        content_layout.addWidget(self.sub)
        content_layout.addWidget(self.weather_label)
        content_layout.addWidget(self.hourly_cloud_bar)
        content_layout.addWidget(self.progress)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{
                background: transparent; color: {COLORS["ink_secondary"]};
                padding: 6px 4px; margin-right: 18px; font-size: 12px;
                font-weight: 600; letter-spacing: 0.5px; border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{ color: {COLORS["ink"]}; border-bottom: 2px solid {COLORS["clay"]}; }}
            """
        )

        # Margin between a card and any opaque, square-cornered child
        # (a QTableWidget's own background, here) must be at least the
        # card's own border-radius (theme.RoundedCard: 16px) — Qt doesn't
        # clip children to a rounded parent on its own, so a smaller
        # margin lets the child's square corners visibly poke out past
        # the card's curve, worst at the bottom two corners.
        _CARD_CONTENT_MARGIN = 16

        shortlist_card = RoundedCard()
        shortlist_layout = QVBoxLayout(shortlist_card)
        shortlist_layout.setContentsMargins(*([_CARD_CONTENT_MARGIN] * 4))
        self.shortlist_export_button = secondary_button("Export CSV…")
        self.shortlist_export_button.setEnabled(False)
        self.shortlist_export_button.clicked.connect(self._on_export_shortlist_csv)
        shortlist_layout.addLayout(self._export_row(self.shortlist_export_button))
        self.shortlist_table = self._build_table(_SHORTLIST_COLUMNS)
        shortlist_layout.addWidget(self.shortlist_table)
        self.tabs.addTab(shortlist_card, "Shortlist")

        ranked_card = RoundedCard()
        ranked_layout = QVBoxLayout(ranked_card)
        ranked_layout.setContentsMargins(*([_CARD_CONTENT_MARGIN] * 4))
        self.ranked_export_button = secondary_button("Export CSV…")
        self.ranked_export_button.setEnabled(False)
        self.ranked_export_button.clicked.connect(self._on_export_ranked_csv)
        ranked_layout.addLayout(self._export_row(self.ranked_export_button))
        self.ranked_table = self._build_table(_RANKED_COLUMNS)
        ranked_layout.addWidget(self.ranked_table)
        self.tabs.addTab(ranked_card, "All ranked")

        self.sky_chart = SkyChartCard()
        self.tabs.addTab(self.sky_chart, "Sky chart")

        self.briefing = BriefingCard()
        self.tabs.addTab(self.briefing, "Briefing")

        self.tabs.addTab(SitesCard(store.SITES), "Sites")
        self.tabs.addTab(RigsCard(store.RIGS), "Rigs")

        content_layout.addWidget(self.tabs, stretch=1)

        self._worker: _PlanWorker | None = None
        # Staged by `_on_plan_ready` for the Export CSV buttons — rebuilding
        # `ShortlistRow`/`RankedRow` from the plan on click, rather than
        # keeping a separate copy of the already-populated table's cell
        # text, is what `_populate_table` itself does too (`shortlist_rows`/
        # `ranked_rows` computed fresh from `plan` each replan).
        self._plan: NightPlan | None = None
        self._local_tz: ZoneInfo | None = None
        self._replan(
            self.sidebar.current_site_record(),
            self.sidebar.current_rig_record(),
            self.sidebar.current_date(),
            self.sidebar.current_limit(),
        )

    @staticmethod
    def _export_row(button: QWidget) -> QHBoxLayout:
        """A right-aligned single-button row above a table — same shape
        `sky_chart.ChartPanel`'s own zoom row uses for its Export PNG
        button, so all three Export actions sit in a consistent spot."""
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(button)
        return row

    def _on_export_shortlist_csv(self) -> None:
        self._export_csv(
            gui_export.shortlist_csv_text(
                data_adapter.build_shortlist_rows(self._plan, self._local_tz)
            ),
            gui_export.DEFAULT_SHORTLIST_CSV_FILENAME,
            "Export Shortlist",
        )

    def _on_export_ranked_csv(self) -> None:
        self._export_csv(
            gui_export.ranked_csv_text(
                data_adapter.build_ranked_rows(self._plan, self._local_tz)
            ),
            gui_export.DEFAULT_RANKED_CSV_FILENAME,
            "Export All Ranked",
        )

    def _export_csv(
        self, csv_text: str, default_filename: str, dialog_title: str
    ) -> None:
        if self._plan is None or self._local_tz is None:
            return
        default_path = str(gui_export.default_export_dir() / default_filename)
        path_str, _ = QFileDialog.getSaveFileName(
            self, dialog_title, default_path, "CSV files (*.csv)"
        )
        if not path_str:
            return
        try:
            gui_export.write_text(csv_text, Path(path_str))
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

    def _build_table(self, columns: list[tuple[str, str, str]]) -> QTableWidget:
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels([label for _key, label, _align in columns])
        for col_index, (key, _label, _align) in enumerate(columns):
            tooltip = _COLUMN_TOOLTIPS.get(key)
            if tooltip is not None:
                table.horizontalHeaderItem(col_index).setToolTip(tooltip)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setFocusPolicy(Qt.NoFocus)
        table.setStyleSheet(
            f"""
            QTableWidget {{ background: {COLORS["paper"]}; border: none; font-size: 13px; }}
            QHeaderView::section {{
                background: {COLORS["paper"]}; color: {COLORS["ink_secondary"]};
                border: none; border-bottom: 1px solid {COLORS["border"]};
                padding: 8px; font-size: 11px; font-weight: 600; letter-spacing: 1px;
            }}
            QTableWidget::item {{ padding: 6px 8px; border-bottom: 1px solid {COLORS["border"]}; }}
            QTableWidget::item:selected {{ background: {COLORS["cream"]}; color: {COLORS["ink"]}; }}
            """
        )
        # Only the Target column stretches to absorb leftover width — every
        # other column sizes to its own absolute minimum (header or cell,
        # whichever is wider) and no further, so Target gets all the space
        # the others don't need. No blanket minimum-section-size floor
        # here anymore — it was padding Alt/Az/Fit/Reach out to 140px each
        # even though their content needs far less; Type's own capped
        # width (below) is what actually protects Target from being
        # squeezed by a long combined-category row.
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col_index, (key, _label, _align) in enumerate(columns):
            if col_index == 0:
                continue
            if key == "type_label":
                # A combined group's categories ("Emission Nebula/Reflection
                # Nebula") can be long — cap this column's width and let it
                # wrap to two lines instead of claiming the space Target
                # needs. Interactive (not ResizeToContents), since
                # ResizeToContents would size to the unwrapped one-line
                # width, defeating the wrap. 140px is the minimum that
                # still fits the longest wrapped line ("Reflection Nebula")
                # without eliding.
                header.setSectionResizeMode(col_index, QHeaderView.Interactive)
                table.setColumnWidth(col_index, 140)
            elif key == "verdict":
                # Fixed, not ResizeToContents: this column holds cell
                # *widgets* (`setCellWidget`), not item text, and Qt's
                # automatic ResizeToContents recompute doesn't reliably
                # apply to those — a column sized for an all-GO/SKIP plan
                # can stay too narrow for a later MARGINAL badge even
                # after an explicit resize. Sized once for the widest
                # possible badge instead, so it's never wrong regardless
                # of what the previous plan needed.
                header.setSectionResizeMode(col_index, QHeaderView.Fixed)
                table.setColumnWidth(col_index, _verdict_column_width())
            else:
                header.setSectionResizeMode(col_index, QHeaderView.ResizeToContents)
        table.setWordWrap(True)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        return table

    def _replan(
        self, site_record: SiteRecord, rig_record: RigRecord, selected_date: date, limit: int
    ) -> None:
        site = site_record.site
        rig = rig_record.rig
        local_tz = ZoneInfo(site.tz)
        when = local_when(selected_date, local_tz)

        self.sidebar.setEnabled(False)
        self.progress.show()
        self.title.setText("Planning…")
        self.sub.setText("")
        self.weather_label.setText("")
        self.hourly_cloud_bar.hide()
        QApplication.setOverrideCursor(Qt.WaitCursor)

        self._worker = _PlanWorker(site, rig, when, limit)
        self._worker.succeeded.connect(
            lambda plan: self._on_plan_ready(plan, local_tz, site, rig, selected_date)
        )
        self._worker.failed.connect(self._on_plan_failed)
        self._worker.start()

    def _on_plan_ready(
        self,
        plan: NightPlan,
        local_tz: ZoneInfo,
        site: Site,
        rig: Rig,
        selected_date: date,
    ) -> None:
        self._finish_replan()
        self._plan = plan
        self._local_tz = local_tz

        summary = data_adapter.build_header_summary(plan, local_tz)
        shortlist_rows = data_adapter.build_shortlist_rows(plan, local_tz)
        ranked_rows = data_adapter.build_ranked_rows(plan, local_tz)
        self.shortlist_export_button.setEnabled(bool(shortlist_rows))
        self.ranked_export_button.setEnabled(bool(ranked_rows))

        self.eyebrow.setText(
            f"{site.name} · {rig.name} · {selected_date:%a %d %b}".upper()
        )
        self.title.setText(title_for_date(selected_date, local_tz))
        self.sub.setText(
            f"{summary.dark_window_text}  ·  Moon {summary.moon_text}  ·  "
            f"{summary.counts_text}"
        )
        self.weather_label.setText(summary.weather_text)
        self.hourly_cloud_bar.set_hourly_cloud_cover(plan.hourly_cloud_cover, local_tz)

        self._populate_table(self.shortlist_table, _SHORTLIST_COLUMNS, shortlist_rows)
        self._populate_table(self.ranked_table, _RANKED_COLUMNS, ranked_rows)
        self.tabs.setTabText(1, f"All ranked ({len(ranked_rows)})")
        self.sky_chart.set_plan(plan, local_tz)
        self.briefing.set_plan(plan)

    def _on_plan_failed(self, message: str) -> None:
        self._finish_replan()
        self.title.setText("Planning failed")
        self.sub.setText(message)

    def _finish_replan(self) -> None:
        QApplication.restoreOverrideCursor()
        self.progress.hide()
        self.sidebar.setEnabled(True)

    def _populate_table(
        self,
        table: QTableWidget,
        columns: list[tuple[str, str, str]],
        rows: list[data_adapter.ShortlistRow] | list[data_adapter.RankedRow],
    ) -> None:
        table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for col_index, (key, _label, align) in enumerate(columns):
                if key == "verdict":
                    table.setCellWidget(
                        row_index, col_index, self._verdict_cell(row.verdict_level)
                    )
                    continue
                item = QTableWidgetItem(getattr(row, key))
                item.setTextAlignment(_ALIGN[align] | Qt.AlignVCenter)
                # Fit/Reach explain the metric itself, since that's what
                # a value under the cursor actually calls for — checked
                # first, since `verdict_reasons` below would otherwise
                # overwrite it on every column of a shortlist row.
                column_tooltip = _COLUMN_TOOLTIPS.get(key)
                if column_tooltip is not None:
                    item.setToolTip(column_tooltip)
                elif hasattr(row, "verdict_reasons"):
                    item.setToolTip("\n".join(row.verdict_reasons))
                table.setItem(row_index, col_index, item)
        # setCellWidget/setItem can shift the "current" cell to whatever
        # was set last (the Verdict column), which drags the horizontal
        # scroll position along with it — force it back so Target is
        # what's visible right after a (re)plan, not the tail columns.
        table.horizontalScrollBar().setValue(0)

    @staticmethod
    def _verdict_cell(level: str) -> QWidget:
        container = QWidget()
        # Same Qt quirk `theme.label_style` works around for QLabel: once
        # any stylesheet exists anywhere in the app, a plain QWidget like
        # this one can start painting an opaque default-palette background
        # instead of staying transparent — visible as a faint box around
        # the pill, most noticeable against GO/SKIP's paler tint.
        container.setStyleSheet("background: transparent;")
        inner = QVBoxLayout(container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(VerdictBadge(level), alignment=Qt.AlignCenter)
        return container

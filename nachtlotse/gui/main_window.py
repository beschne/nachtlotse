"""The main window: sidebar + tonight's shortlist.

Wires real data end to end — `planning.plan_night` against whichever
site/rig/date is staged in the sidebar. No illustrative sample data
anywhere in this package (unlike `macos-app-spike/`, which was never
meant to be kept — see its README.md).

Every screen from the original scaffolding plan is now here: the
shortlist, the full ranked table, the polar sky chart, the LLM
briefing, and a read-only sites/rigs reference screen (see
`sites_rigs.py`'s own docstring for why it's read-only, not an editor).
"""

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from nachtlotse import planning
from nachtlotse.data import store
from nachtlotse.data.store import RigRecord, SiteRecord
from nachtlotse.gui import data_adapter
from nachtlotse.gui.briefing import BriefingCard
from nachtlotse.gui.sidebar import Sidebar
from nachtlotse.gui.sites_rigs import SitesRigsCard
from nachtlotse.gui.sky_chart import SkyChartCard
from nachtlotse.gui.theme import COLORS, RoundedCard, VerdictBadge, label_style

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


def local_when(selected_date: date, local_tz: ZoneInfo) -> datetime:
    """Noon local time on `selected_date` — unambiguously daytime, so
    `constraints.dark_window` picks the night starting that evening.
    Mirrors `cli.py`'s `_resolve_when`."""
    return datetime.combine(selected_date, time(12, 0), tzinfo=local_tz)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Nachtlotse")
        self.resize(1080, 640)

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
            label_style(f"color: {COLORS['ink_secondary']}; font-size: 12px; margin-bottom: 12px;")
        )

        content_layout.addWidget(self.eyebrow)
        content_layout.addWidget(self.title)
        content_layout.addWidget(self.sub)
        content_layout.addWidget(self.weather_label)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{
                background: transparent; color: {COLORS['ink_secondary']};
                padding: 6px 4px; margin-right: 18px; font-size: 12px;
                font-weight: 600; letter-spacing: 0.5px; border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{ color: {COLORS['ink']}; border-bottom: 2px solid {COLORS['clay']}; }}
            """
        )

        shortlist_card = RoundedCard()
        shortlist_layout = QVBoxLayout(shortlist_card)
        shortlist_layout.setContentsMargins(8, 8, 8, 8)
        self.shortlist_table = self._build_table(_SHORTLIST_COLUMNS)
        shortlist_layout.addWidget(self.shortlist_table)
        self.tabs.addTab(shortlist_card, "Shortlist")

        ranked_card = RoundedCard()
        ranked_layout = QVBoxLayout(ranked_card)
        ranked_layout.setContentsMargins(8, 8, 8, 8)
        self.ranked_table = self._build_table(_RANKED_COLUMNS)
        ranked_layout.addWidget(self.ranked_table)
        self.tabs.addTab(ranked_card, "All ranked")

        self.sky_chart = SkyChartCard()
        self.tabs.addTab(self.sky_chart, "Sky chart")

        self.briefing = BriefingCard()
        self.tabs.addTab(self.briefing, "Briefing")

        self.tabs.addTab(SitesRigsCard(store.SITES, store.RIGS), "Sites & Rigs")

        content_layout.addWidget(self.tabs, stretch=1)

        self._replan(
            self.sidebar.current_site_record(),
            self.sidebar.current_rig_record(),
            self.sidebar.current_date(),
        )

    def _build_table(self, columns: list[tuple[str, str, str]]) -> QTableWidget:
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels([label for _key, label, _align in columns])
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setFocusPolicy(Qt.NoFocus)
        table.setStyleSheet(
            f"""
            QTableWidget {{ background: {COLORS['paper']}; border: none; font-size: 13px; }}
            QHeaderView::section {{
                background: {COLORS['paper']}; color: {COLORS['ink_secondary']};
                border: none; border-bottom: 1px solid {COLORS['border']};
                padding: 8px; font-size: 11px; font-weight: 600; letter-spacing: 1px;
            }}
            QTableWidget::item {{ padding: 6px 8px; border-bottom: 1px solid {COLORS['border']}; }}
            QTableWidget::item:selected {{ background: {COLORS['cream']}; color: {COLORS['ink']}; }}
            """
        )
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        return table

    def _replan(self, site_record: SiteRecord, rig_record: RigRecord, selected_date: date) -> None:
        site = site_record.site
        rig = rig_record.rig
        local_tz = ZoneInfo(site.tz)
        when = local_when(selected_date, local_tz)

        plan = planning.plan_night(site, rig, when)
        summary = data_adapter.build_header_summary(plan, local_tz)
        shortlist_rows = data_adapter.build_shortlist_rows(plan, local_tz)
        ranked_rows = data_adapter.build_ranked_rows(plan, local_tz)

        self.eyebrow.setText(
            f"{site.name} · {rig.name} · {selected_date:%a %d %b}".upper()
        )
        self.sub.setText(
            f"{summary.dark_window_text}  ·  Moon {summary.moon_text}  ·  "
            f"{summary.counts_text}"
        )
        self.weather_label.setText(summary.weather_text)

        self._populate_table(self.shortlist_table, _SHORTLIST_COLUMNS, shortlist_rows)
        self._populate_table(self.ranked_table, _RANKED_COLUMNS, ranked_rows)
        self.tabs.setTabText(1, f"All ranked ({len(ranked_rows)})")
        self.sky_chart.set_plan(plan, local_tz)
        self.briefing.set_plan(plan)

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
                    table.setCellWidget(row_index, col_index, self._verdict_cell(row.verdict_level))
                    continue
                item = QTableWidgetItem(getattr(row, key))
                item.setTextAlignment(_ALIGN[align] | Qt.AlignVCenter)
                if hasattr(row, "verdict_reasons"):
                    item.setToolTip("\n".join(row.verdict_reasons))
                table.setItem(row_index, col_index, item)

    @staticmethod
    def _verdict_cell(level: str) -> QWidget:
        container = QWidget()
        inner = QVBoxLayout(container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(VerdictBadge(level), alignment=Qt.AlignCenter)
        return container

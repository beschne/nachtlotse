"""The "Best sky" tab — `best_sky.compare_sites` surfaced in the GUI
(closed roadmap item: "'Best sky' in the GUI", ROADMAP.md).

A different question from the main Shortlist/All ranked/Sky chart tabs,
which all plan against whichever single site is staged in the sidebar:
this tab answers "which of my configured sites has the clearest sky
tonight", independent of any rig. It therefore doesn't hook into
`MainWindow._replan` at all — its own Center/Radius controls are staged
and applied by their own Refresh button (same "staged, not live" rule
`sidebar.py`'s module docstring lays out), not tied to the sidebar's
Re-plan.

The compared date instead *does* follow the sidebar: `set_date` is
called from `MainWindow._on_plan_ready` after every successful plan, so
Best Sky always compares the same night currently being planned rather
than needing a second date picker of its own. It's a passive update,
though — changing the sidebar's date doesn't itself trigger a network
refetch here; only clicking Refresh does, so switching site/rig/date on
the main sidebar can never silently fire an extra round of per-site
Open-Meteo requests.

The request runs on a background `QThread` (`_BestSkyWorker`), same
reasoning as `briefing._BriefingWorker`/`main_window._PlanWorker`: it's
one Open-Meteo fetch per candidate site (cached 1h, but still real
network I/O), and running it on the UI thread would freeze the window.
"""

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from nachtlotse import best_sky
from nachtlotse.data.store import SiteRecord
from nachtlotse.gui import data_adapter
from nachtlotse.gui.hourly_cloud_bar import build_cloud_sparkline
from nachtlotse.gui.theme import COLORS, RoundedCard, label_style, secondary_button

# Sites you'd realistically drive to for one night, not a hard engine
# limit — best_sky.compare_sites itself accepts any distance.
_MAX_RADIUS_KM = 500

# "Clouds up to" carries the phrasing that used to repeat in every row's
# own cell text (data_adapter.BestSkyRow.clouds_text is now just the
# numbers) — and "Tonight" is the hourly sparkline column, the widest
# one, so it gets the header resize Stretch below.
_COLUMN_HEADERS = ["Site", "Distance", "Clouds up to", "Tonight"]
_TONIGHT_COLUMN_INDEX = 3


def _local_when(selected_date: date, local_tz: ZoneInfo) -> datetime:
    """Noon local time on `selected_date` — same reasoning as
    `main_window.local_when` (unambiguously daytime, so
    `constraints.dark_window` picks the night starting that evening);
    duplicated rather than imported to avoid a `main_window` <->
    `best_sky_card` import cycle."""
    return datetime.combine(selected_date, time(12, 0), tzinfo=local_tz)


class _BestSkyWorker(QThread):
    """Runs `best_sky.compare_sites` off the UI thread."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        reference: SiteRecord,
        candidates: list[SiteRecord],
        selected_date: date,
        max_distance_km: float | None,
    ) -> None:
        super().__init__()
        self._reference = reference
        self._candidates = candidates
        self._selected_date = selected_date
        self._max_distance_km = max_distance_km

    def run(self) -> None:
        when = _local_when(self._selected_date, ZoneInfo(self._reference.site.tz))
        try:
            reports = best_sky.compare_sites(
                self._reference.site,
                [record.site for record in self._candidates],
                when,
                max_distance_km=self._max_distance_km,
            )
        except Exception as exc:  # noqa: BLE001 — surface any failure to the UI, don't crash it
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(reports)


class BestSkyCard(RoundedCard):
    """Center/Radius controls, a Refresh button, and the ranked
    clearest-first comparison table."""

    plan_site_requested = Signal(object)  # SiteRecord

    def __init__(self, sites: list[SiteRecord]) -> None:
        super().__init__()
        if not sites:
            raise ValueError("BestSkyCard needs at least one configured site")
        self._sites = sites
        # A placeholder until the sidebar's own first plan completes and
        # calls `set_date` for real (see module docstring) — the system's
        # local date is a fine starting guess for that brief window.
        self._selected_date = datetime.now().astimezone().date()
        self._rows: list[data_adapter.BestSkyRow] = []
        self._worker: _BestSkyWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QLabel("Best sky")
        header.setStyleSheet(
            label_style(f"color: {COLORS['ink']}; font-size: 16px; font-weight: 600;")
        )
        layout.addWidget(header)

        controls_style = f"""
            QComboBox, QSpinBox {{
                background: {COLORS['cream']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 12px;
                color: {COLORS['ink']};
            }}
        """

        controls_row = QHBoxLayout()
        controls_row.addWidget(self._field_label("CENTER"))
        self.center_combo = QComboBox()
        for record in sites:
            self.center_combo.addItem(record.site.name)
        self.center_combo.setStyleSheet(controls_style)
        controls_row.addWidget(self.center_combo)

        controls_row.addWidget(self._field_label("RADIUS"))
        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(0, _MAX_RADIUS_KM)
        self.radius_spin.setSingleStep(10)
        self.radius_spin.setSuffix(" km")
        # 0 means "no cap", mirroring the CLI's own `--radius-km`
        # (omitted = every configured site) and the EVALUATE spinbox's
        # identical 0-is-special convention in sidebar.py.
        self.radius_spin.setSpecialValueText("All sites")
        self.radius_spin.setStyleSheet(controls_style)
        controls_row.addWidget(self.radius_spin)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS["clay"]}; color: {COLORS["text_on_accent"]};
                border: none; border-radius: 8px; padding: 6px 16px;
                font-size: 12px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS["clay_hover"]}; }}
            QPushButton:pressed {{ background: {COLORS["clay_press"]}; }}
            QPushButton:disabled {{
                background: {COLORS["border_strong"]}; color: {COLORS["ink_muted"]};
            }}
            """
        )
        self.refresh_button.clicked.connect(self._on_refresh_clicked)
        controls_row.addWidget(self.refresh_button)
        controls_row.addStretch(1)
        layout.addLayout(controls_row)

        self.status_label = QLabel("Pick a center site and click Refresh.")
        self.status_label.setStyleSheet(
            label_style(f"color: {COLORS['ink_secondary']}; font-size: 12px;")
        )
        layout.addWidget(self.status_label)

        self.table = self._build_table()
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table, stretch=1)

        self.plan_button = secondary_button("Plan this site")
        self.plan_button.setEnabled(False)
        self.plan_button.clicked.connect(self._on_plan_clicked)
        plan_row = QHBoxLayout()
        plan_row.addStretch(1)
        plan_row.addWidget(self.plan_button)
        layout.addLayout(plan_row)

    @staticmethod
    def _field_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            label_style(
                f"color: {COLORS['ink_secondary']}; font-size: 11px; "
                "font-weight: 600; letter-spacing: 0.8px;"
            )
        )
        return label

    def _build_table(self) -> QTableWidget:
        table = QTableWidget(0, len(_COLUMN_HEADERS))
        table.setHorizontalHeaderLabels(_COLUMN_HEADERS)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
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
        header = table.horizontalHeader()
        for col_index in range(len(_COLUMN_HEADERS)):
            if col_index == _TONIGHT_COLUMN_INDEX:
                header.setSectionResizeMode(col_index, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(col_index, QHeaderView.ResizeToContents)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        return table

    def set_center(self, site_record: SiteRecord) -> None:
        """Called once at startup to default Center to whatever site the
        main sidebar is already showing — a sensible starting point, not
        kept in sync afterwards (the two controls are independent, see
        module docstring)."""
        self.center_combo.setCurrentIndex(self._sites.index(site_record))

    def set_date(self, selected_date: date) -> None:
        """Called from `MainWindow._on_plan_ready` after every successful
        plan — see module docstring for why this doesn't itself trigger
        a refetch."""
        self._selected_date = selected_date

    def _on_refresh_clicked(self) -> None:
        reference = self._sites[self.center_combo.currentIndex()]
        radius_value = self.radius_spin.value()
        max_distance_km = float(radius_value) if radius_value > 0 else None

        self.refresh_button.setEnabled(False)
        self.plan_button.setEnabled(False)
        self.status_label.setStyleSheet(
            label_style(f"color: {COLORS['ink_secondary']}; font-size: 12px;")
        )
        self.status_label.setText(
            f"Comparing sites near {reference.site.name} for the night of "
            f"{self._selected_date:%A, %B %-d}…"
        )
        self.table.setRowCount(0)

        self._worker = _BestSkyWorker(reference, self._sites, self._selected_date, max_distance_km)
        self._worker.succeeded.connect(self._on_succeeded)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_succeeded(self, reports: list[best_sky.SiteSkyReport]) -> None:
        self.refresh_button.setEnabled(True)
        self._rows = data_adapter.build_best_sky_rows(reports, self._sites)
        self.table.setRowCount(len(self._rows))
        for row_index, row in enumerate(self._rows):
            site_item = QTableWidgetItem(row.site_text)
            distance_item = QTableWidgetItem(row.distance_text)
            clouds_item = QTableWidgetItem(row.clouds_text)
            if not row.clouds_available:
                clouds_item.setForeground(Qt.gray)
            for item in (site_item, distance_item, clouds_item):
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.table.setItem(row_index, 0, site_item)
            self.table.setItem(row_index, 1, distance_item)
            self.table.setItem(row_index, 2, clouds_item)
            local_tz = ZoneInfo(row.site_record.site.tz)
            self.table.setCellWidget(
                row_index,
                _TONIGHT_COLUMN_INDEX,
                build_cloud_sparkline(row.hourly_cloud_cover, local_tz),
            )
        if self._rows:
            self.table.selectRow(0)  # the clearest site, already ranked first
            self.status_label.setText(f"{len(self._rows)} site(s) compared.")
        else:
            self.status_label.setText("No configured site falls within that radius.")

    def _on_failed(self, message: str) -> None:
        self.refresh_button.setEnabled(True)
        self.status_label.setStyleSheet(
            label_style(f"color: {COLORS['skip_text']}; font-size: 12px;")
        )
        self.status_label.setText(message)

    def _on_selection_changed(self) -> None:
        self.plan_button.setEnabled(bool(self.table.selectedItems()))

    def _on_plan_clicked(self) -> None:
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = self._rows[selected_rows[0].row()]
        self.plan_site_requested.emit(row.site_record)

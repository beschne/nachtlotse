"""The left-hand controls box: site/rig/date pickers plus a Re-plan
button — see macos-app-spike/README.md for where this layout came from
(the PySide6-vs-PyObjC framework spike).

Selections are staged, not applied live: changing a combo box or the
date only updates what *would* be planned; nothing re-runs `planning`
until Re-plan is clicked (`replan_requested`) — computing a real plan
touches ephemeris and (optionally) the network, so it shouldn't fire on
every keystroke/click the way the spike's cosmetic eyebrow-text update
could afford to.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import QComboBox, QDateEdit, QLabel, QPushButton, QVBoxLayout

from nachtlotse.data.store import RigRecord, SiteRecord
from nachtlotse.gui.theme import COLORS, RoundedCard, label_style

SIDEBAR_WIDTH = 240


class Sidebar(RoundedCard):
    """Emits `replan_requested` with the currently-staged (site record,
    rig record, date) when the user clicks Re-plan."""

    replan_requested = Signal(object, object, date)

    def __init__(self, sites: list[SiteRecord], rigs: list[RigRecord]) -> None:
        super().__init__()
        if not sites:
            raise ValueError("Sidebar needs at least one configured site")
        if not rigs:
            raise ValueError("Sidebar needs at least one configured rig")

        self._sites = sites
        self._rigs = rigs

        self.setFixedWidth(SIDEBAR_WIDTH)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(4)

        wordmark = QLabel("Nachtlotse")
        wordmark.setStyleSheet(
            label_style(f"color: {COLORS['ink']}; font-size: 19px; font-weight: 600; margin-bottom: 18px;")
        )
        layout.addWidget(wordmark)

        picker_style = f"""
            QComboBox, QDateEdit {{
                background: {COLORS['cream']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 6px 28px 6px 10px;
                font-size: 13px;
                color: {COLORS['ink']};
            }}
            QComboBox::drop-down, QDateEdit::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background: {COLORS['paper']};
                color: {COLORS['ink']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                outline: none;
                padding: 4px;
                selection-background-color: {COLORS['cream']};
                selection-color: {COLORS['ink']};
            }}
        """
        field_label_style = label_style(
            f"color: {COLORS['ink_secondary']}; font-size: 11px; font-weight: 600; "
            "letter-spacing: 0.8px; margin-top: 10px;"
        )

        site_label = QLabel("SITE")
        site_label.setStyleSheet(field_label_style)
        self.site_combo = QComboBox()
        for record in sites:
            self.site_combo.addItem(record.site.name)
        self.site_combo.setStyleSheet(picker_style)

        rig_label = QLabel("RIG")
        rig_label.setStyleSheet(field_label_style)
        self.rig_combo = QComboBox()
        for record in rigs:
            self.rig_combo.addItem(record.rig.name)
        self.rig_combo.setStyleSheet(picker_style)

        date_label = QLabel("DATE")
        date_label.setStyleSheet(field_label_style)
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("ddd d MMM")
        self.date_edit.setStyleSheet(picker_style)

        for widget in (site_label, self.site_combo, rig_label, self.rig_combo, date_label, self.date_edit):
            layout.addWidget(widget)

        layout.addStretch(1)

        replan_button = QPushButton("Re-plan")
        replan_button.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS['clay']};
                color: {COLORS['text_on_accent']};
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS['clay_hover']}; }}
            QPushButton:pressed {{ background: {COLORS['clay_press']}; }}
            """
        )
        replan_button.clicked.connect(self._emit_replan)
        layout.addWidget(replan_button)

    def _emit_replan(self) -> None:
        site_record = self._sites[self.site_combo.currentIndex()]
        rig_record = self._rigs[self.rig_combo.currentIndex()]
        selected_date = self.date_edit.date().toPython()
        self.replan_requested.emit(site_record, rig_record, selected_date)

    def current_site_record(self) -> SiteRecord:
        return self._sites[self.site_combo.currentIndex()]

    def current_rig_record(self) -> RigRecord:
        return self._rigs[self.rig_combo.currentIndex()]

    def current_date(self) -> date:
        return self.date_edit.date().toPython()

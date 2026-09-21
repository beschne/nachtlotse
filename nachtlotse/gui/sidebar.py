"""The left-hand controls box: site/rig/date pickers plus a Re-plan
button — this layout (a sidebar box of pickers + button) came out of the
PySide6-vs-PyObjC framework spike that settled ROADMAP.md's native macOS
app toolkit decision (the throwaway spike itself is gone; PySide6 won).

Selections are staged, not applied live: changing a combo box or the
date only updates what *would* be planned; nothing re-runs `planning`
until Re-plan is clicked (`replan_requested`) — computing a real plan
touches ephemeris and (optionally) the network, so it shouldn't fire on
every keystroke/click.

Re-plan starts disabled and only re-enables once something is staged
that differs from the last computed plan — so changing site, rig, *and*
date all takes one click, not three redundant re-plans in between.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, QLocale, Signal
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import QComboBox, QDateEdit, QLabel, QPushButton, QVBoxLayout

from nachtlotse.data.store import RigRecord, SiteRecord
from nachtlotse.gui.theme import COLORS, RoundedCard, label_style

SIDEBAR_WIDTH = 300


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
                padding: 6px 26px 6px 8px;
                font-size: 12px;
                color: {COLORS['ink']};
            }}
            QComboBox::drop-down, QDateEdit::drop-down {{
                border: none;
                width: 24px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
            }}
            QComboBox::drop-down:hover, QDateEdit::drop-down:hover {{
                background: {COLORS['cream_hover']};
                border-radius: 6px;
            }}
            QComboBox::down-arrow, QDateEdit::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {COLORS['ink_secondary']};
                margin-right: 10px;
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
        self.date_edit.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("ddd d MMMM")
        self.date_edit.setStyleSheet(picker_style)
        self.date_edit.calendarWidget().setLocale(self.date_edit.locale())
        self.date_edit.calendarWidget().setStyleSheet(
            f"""
            QCalendarWidget QWidget {{ background: {COLORS['paper']}; color: {COLORS['ink']}; }}
            QCalendarWidget QToolButton {{
                background: transparent; color: {COLORS['ink']};
                font-size: 13px; font-weight: 600;
            }}
            QCalendarWidget QToolButton:hover {{ background: {COLORS['cream_hover']}; border-radius: 6px; }}
            QCalendarWidget QAbstractItemView:enabled {{
                background: {COLORS['paper']}; color: {COLORS['ink']};
                selection-background-color: {COLORS['clay']};
                selection-color: {COLORS['text_on_accent']};
                outline: none;
            }}
            QCalendarWidget QAbstractItemView:disabled {{ color: {COLORS['ink_muted']}; }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {COLORS['cream']}; }}
            """
        )
        # Mark today distinctly from the currently-selected date (which
        # already gets the solid-clay selection style above) — a light
        # clay tint plus bold, so "today" and "the staged date" read as
        # two different things even when they're not the same day.
        today_format = QTextCharFormat()
        today_format.setBackground(QColor(COLORS["clay_tint"]))
        today_format.setForeground(QColor(COLORS["clay_hover"]))
        today_format.setFontWeight(700)
        self.date_edit.calendarWidget().setDateTextFormat(QDate.currentDate(), today_format)

        for widget in (site_label, self.site_combo, rig_label, self.rig_combo, date_label, self.date_edit):
            layout.addWidget(widget)

        layout.addStretch(1)

        self.replan_button = QPushButton("Re-plan")
        self.replan_button.setStyleSheet(
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
            QPushButton:disabled {{
                background: {COLORS['border_strong']};
                color: {COLORS['ink_muted']};
            }}
            """
        )
        self.replan_button.setEnabled(False)  # nothing staged differs from the plan shown yet
        self.replan_button.clicked.connect(self._emit_replan)
        layout.addWidget(self.replan_button)

        # Any staged change re-enables Re-plan; clicking it applies the
        # change and goes back to disabled — lets you change site, rig,
        # *and* date together and replan once, instead of on every click.
        self.site_combo.currentIndexChanged.connect(self._mark_dirty)
        self.rig_combo.currentIndexChanged.connect(self._mark_dirty)
        self.date_edit.dateChanged.connect(self._mark_dirty)

    def _mark_dirty(self, *_args: object) -> None:
        self.replan_button.setEnabled(True)

    def _emit_replan(self) -> None:
        site_record = self._sites[self.site_combo.currentIndex()]
        rig_record = self._rigs[self.rig_combo.currentIndex()]
        selected_date = self.date_edit.date().toPython()
        self.replan_requested.emit(site_record, rig_record, selected_date)
        self.replan_button.setEnabled(False)

    def current_site_record(self) -> SiteRecord:
        return self._sites[self.site_combo.currentIndex()]

    def current_rig_record(self) -> RigRecord:
        return self._rigs[self.rig_combo.currentIndex()]

    def current_date(self) -> date:
        return self.date_edit.date().toPython()

"""Hourly cloud-cover strip: the GUI counterpart to `cli.py`'s ASCII
sparkline (ROADMAP.md's "Hourly cloud cover for the astro-night") — one
colored cell per forecast hour across the dark window, instead of one
averaged max/avg number collapsing a clear-then-socked-in (or the
reverse) night into a single misleading percentage.

Color bands are the user's own clearoutside.com-inspired thresholds
(0-18% good, 19-48% moderate, 49-100% poor), but drawn from this app's
own muted verdict palette (`theme.VERDICT_COLORS`' `_text` tones — the
same ones `sky_chart._verdict_line_color` already draws GO/MARGINAL/SKIP
tracks with) rather than clearoutside's own saturated blue gradient or a
generic traffic-light red/yellow/green — explicitly asked for as "the
GUI theme's own palette, no signal colors".
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from nachtlotse.gui.theme import COLORS, label_style
from nachtlotse.weather.open_meteo import HourlyWeather

# Thresholds as given: "good" up to 18%, "moderate" 19-48%, "poor" above.
_GOOD_MAX_PCT = 18.0
_MODERATE_MAX_PCT = 48.0


def _band_color(cloud_cover_pct: float) -> str:
    if cloud_cover_pct <= _GOOD_MAX_PCT:
        return COLORS["go_text"]
    if cloud_cover_pct <= _MODERATE_MAX_PCT:
        return COLORS["marginal_text"]
    return COLORS["skip_text"]


class _CloudStrip(QWidget):
    """Paints the colored cells, each labeled with its own local hour.
    Hover still shows the exact hour and percentage as a tooltip — the
    color band and the hour number alone don't give the precise
    percentage, same as a colored map legend needing its own key.

    `compact`, used for `build_cloud_sparkline` below (a per-row table
    cell, e.g. `gui/best_sky_card.py`'s results table): no caption/range
    label above it (that's `HourlyCloudCoverBar`'s own job) and a lower
    minimum width, so it still fits a narrower table column — but the
    same height and per-cell hour digits as the standalone bar, not a
    plain unlabeled color strip.
    """

    _HEIGHT = 24
    _GAP = 2.0

    def __init__(self, *, compact: bool = False) -> None:
        super().__init__()
        self._hours: list[tuple[datetime, float]] = []
        self._local_tz: ZoneInfo | None = None
        self.setFixedHeight(self._HEIGHT)
        self.setMinimumWidth(60 if compact else 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)

    def set_hours(self, hours: list[tuple[datetime, float]], local_tz: ZoneInfo) -> None:
        self._hours = hours
        self._local_tz = local_tz
        self.update()

    def _cell_rects(self) -> list[QRectF]:
        n = len(self._hours)
        if n == 0:
            return []
        total_gap = self._GAP * (n - 1)
        cell_w = (self.width() - total_gap) / n
        return [QRectF(i * (cell_w + self._GAP), 0, cell_w, self.height()) for i in range(n)]

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font = QFont()
        font.setPointSizeF(9.0)
        painter.setFont(font)
        text_color = QColor(COLORS["text_on_accent"])
        for rect, (when, cloud_cover_pct) in zip(self._cell_rects(), self._hours, strict=True):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(_band_color(cloud_cover_pct)))
            painter.drawRoundedRect(rect, 3.0, 3.0)

            local_hour = when.astimezone(self._local_tz).hour if self._local_tz else when.hour
            painter.setPen(text_color)
            painter.drawText(rect, Qt.AlignCenter, f"{local_hour:02d}")
        painter.end()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        for rect, (when, cloud_cover_pct) in zip(self._cell_rects(), self._hours, strict=True):
            if rect.contains(event.position()):
                local_time = when.astimezone(self._local_tz) if self._local_tz else when
                self.setToolTip(f"{local_time:%H:%M} — {cloud_cover_pct:.0f}% cloud cover")
                return
        self.setToolTip("")

    def leaveEvent(self, event) -> None:
        self.setToolTip("")


class HourlyCloudCoverBar(QWidget):
    """A caption, the colored strip, and the covered time range — one
    line above the strip, mirroring `cli.py`'s own sparkline line.
    Hides itself entirely when there's nothing to show (no hourly
    forecast reached the dark window), the same "no data" fallback
    `cli.py`'s `_hourly_cloud_cover_line` uses by returning None.
    """

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)

        caption_row = QHBoxLayout()
        caption_row.setContentsMargins(0, 0, 0, 0)
        caption = QLabel("Clouds, hour by hour")
        caption.setStyleSheet(label_style(f"color: {COLORS['ink_secondary']}; font-size: 11px;"))
        self._range_label = QLabel()
        self._range_label.setStyleSheet(
            label_style(f"color: {COLORS['ink_muted']}; font-size: 11px;")
        )
        caption_row.addWidget(caption)
        caption_row.addStretch(1)
        caption_row.addWidget(self._range_label)
        layout.addLayout(caption_row)

        self._strip = _CloudStrip()
        layout.addWidget(self._strip)

    def set_hourly_cloud_cover(self, hourly: list[HourlyWeather], local_tz: ZoneInfo) -> None:
        hours = [(hour.when, hour.cloud_cover_pct) for hour in hourly]
        self._strip.set_hours(hours, local_tz)
        if not hours:
            self._range_label.setText("")
            self.hide()
            return
        start_local = hours[0][0].astimezone(local_tz)
        end_local = hours[-1][0].astimezone(local_tz)
        self._range_label.setText(f"{start_local:%H:%M}–{end_local:%H:%M} {end_local:%Z}")
        self.show()


def build_cloud_sparkline(hourly: list[HourlyWeather], local_tz: ZoneInfo) -> QWidget:
    """A caption-less hourly cloud-cover strip for embedding as a table
    cell widget (`gui/best_sky_card.py`'s results table) — same color
    bands, per-cell hour digits, and hover tooltip as
    `HourlyCloudCoverBar`, just without the caption/range label above
    it (that line belongs once per screen, not once per row). One-shot,
    like `main_window._verdict_cell`: built fresh each time the table
    repopulates, no `set_*` method of its own."""
    strip = _CloudStrip(compact=True)
    strip.set_hours([(hour.when, hour.cloud_cover_pct) for hour in hourly], local_tz)
    return strip

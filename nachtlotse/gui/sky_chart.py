"""Tonight's polar sky chart — QPainter-rendered, reusing `charting.py`'s
pure alt/az projection geometry (the same module `lotse plan --chart`'s
matplotlib PNG export uses). No new astronomy here, same as that module.

Colored by verdict (GO/MARGINAL/SKIP) instead of the CLI PNG's
categorical per-target palette — this view sits right next to the
shortlist table, where verdict color already carries meaning
(`theme.VerdictBadge`). The canvas always renders on the dark
`theme.SKY_COLORS` regardless of the app's own (currently light-only)
theme — a night sky doesn't get a light-mode variant, see theme.py.

Deliberately not drawn: the moon's own position. The engine doesn't
track moon altitude/azimuth anywhere yet (only illumination %, see
`planning.NightPlan.moon_illumination_pct`), and this module invents no
astronomy the engine hasn't computed (Guiding principle, CLAUDE.md).
"""

from __future__ import annotations

import re

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from nachtlotse import charting
from nachtlotse.gui import data_adapter
from nachtlotse.gui.theme import SKY_COLORS
from nachtlotse.planning import NightPlan, NightPlanForBestRig

_VERDICT_SKY_KEY = {"GO": "go", "MARGINAL": "marginal", "SKIP": "skip"}

# Chart-space coordinates from `charting.project()` range roughly -98..98
# (the rim sits at r=90, compass labels a touch further out) — this is
# the half-extent used to scale into pixels.
_CHART_HALF_EXTENT = 100.0


def _qcolor(value: str) -> QColor:
    """Accepts the two shapes `theme.SKY_COLORS` uses: "#rrggbb" and
    "rgba(r, g, b, a)" with a 0-1 alpha — Qt's own QColor doesn't parse
    the latter directly."""
    if value.startswith("#"):
        return QColor(value)
    match = re.match(r"rgba\(\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)\s*\)", value)
    if not match:
        raise ValueError(f"Unrecognized color value: {value!r}")
    r, g, b, a = match.groups()
    return QColor(int(float(r)), int(float(g)), int(float(b)), round(float(a) * 255))


class SkyChartCanvas(QWidget):
    """Paints the polar chart for whatever plan was last staged via
    `set_plan` — nothing is drawn until a plan with a non-empty
    shortlist arrives."""

    def __init__(self) -> None:
        super().__init__()
        self._plan: NightPlan | NightPlanForBestRig | None = None
        self.setMinimumSize(320, 320)

    def set_plan(self, plan: NightPlan | NightPlanForBestRig) -> None:
        self._plan = plan
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), _qcolor(SKY_COLORS["canvas"]))

        if self._plan is None or not self._plan.shortlist:
            painter.setPen(_qcolor(SKY_COLORS["label"]))
            painter.drawText(self.rect(), Qt.AlignCenter, "No shortlisted targets to chart tonight.")
            painter.end()
            return

        cx, cy = self.width() / 2.0, self.height() / 2.0
        scale = (min(self.width(), self.height()) / 2.0 - 12) / _CHART_HALF_EXTENT

        def to_px(point: tuple[float, float]) -> QPointF:
            x, y = point
            return QPointF(cx + x * scale, cy - y * scale)

        self._paint_horizon_wedge(painter, to_px)
        self._paint_grid(painter, to_px)
        self._paint_compass_labels(painter, to_px)
        self._paint_tracks(painter, to_px)
        painter.end()

    def _paint_horizon_wedge(self, painter: QPainter, to_px) -> None:
        wedge = charting.horizon_wedge(self._plan.site)
        path = QPainterPath()
        path.moveTo(to_px(wedge[0]))
        for point in wedge[1:]:
            path.lineTo(to_px(point))
        path.closeSubpath()
        painter.setPen(Qt.NoPen)
        painter.setBrush(_qcolor(SKY_COLORS["rim"]))
        painter.drawPath(path)

    def _paint_grid(self, painter: QPainter, to_px) -> None:
        painter.setBrush(Qt.NoBrush)  # else the wedge's leftover fill bleeds into these outlines
        font = QFont()
        font.setPointSizeF(8.0)
        painter.setFont(font)
        for alt_deg in charting.GRID_RINGS_ALT_DEG:
            ring = [to_px(p) for p in charting.grid_ring(alt_deg)]
            pen = QPen(_qcolor(SKY_COLORS["grid_strong"] if alt_deg == 0.0 else SKY_COLORS["grid"]))
            pen.setWidthF(1.2 if alt_deg == 0.0 else 0.75)
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(ring[0])
            for point in ring[1:]:
                path.lineTo(point)
            painter.drawPath(path)

            if alt_deg == 0.0:
                continue  # the 0° ring is the rim itself; no separate label
            label_point = to_px(charting.project(alt_deg, az_deg=0.0))
            painter.setPen(_qcolor(SKY_COLORS["label"]))
            painter.drawText(
                QRectF(label_point.x() - 20, label_point.y() - 16, 40, 14),
                Qt.AlignCenter,
                f"{alt_deg:.0f}°",
            )

    def _paint_compass_labels(self, painter: QPainter, to_px) -> None:
        font = QFont()
        font.setPointSizeF(10.0)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(_qcolor(SKY_COLORS["label"]))
        for label, az_deg in charting.COMPASS_LABELS:
            point = to_px(charting.compass_label_point(az_deg, rim_r=97.0))
            painter.drawText(QRectF(point.x() - 12, point.y() - 10, 24, 20), Qt.AlignCenter, label)

    def _paint_tracks(self, painter: QPainter, to_px) -> None:
        painter.setBrush(Qt.NoBrush)
        tracks = charting.shortlist_tracks(self._plan)
        for entry, track in zip(self._plan.shortlist, tracks):
            color = _qcolor(SKY_COLORS[_VERDICT_SKY_KEY[entry.verdict.level]])
            pen = QPen(color)
            pen.setWidthF(2.4)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            for segment in track.segments:
                if len(segment) < 2:
                    continue
                path = QPainterPath()
                path.moveTo(to_px(segment[0]))
                for point in segment[1:]:
                    path.lineTo(to_px(point))
                painter.drawPath(path)

            # Mark the entry's scored best-time position with a filled dot.
            best_point = to_px(charting.project(entry.ranked.pos.alt_deg, entry.ranked.pos.az_deg))
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(best_point, 4.0, 4.0)


class _SkyChartFrame(QFrame):
    """Same rounded-card visual language as `theme.RoundedCard`, but
    always dark (`SKY_COLORS`) regardless of app theme — kept separate
    rather than parameterizing `RoundedCard`, since every other card in
    the app is meant to flip with a future light/dark toggle and this
    one deliberately never should."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("skyChartFrame")
        self.setStyleSheet(
            f"""
            QFrame#skyChartFrame {{
                background: {SKY_COLORS["canvas"]};
                border-radius: 16px;
                border: 1px solid {SKY_COLORS["rim"]};
            }}
            """
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)


class SkyChartCard(_SkyChartFrame):
    """The chart canvas plus a legend column naming each shortlisted
    entry and its verdict color."""

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        self.canvas = SkyChartCanvas()
        layout.addWidget(self.canvas, stretch=1)

        self._legend_layout = QVBoxLayout()
        self._legend_layout.setContentsMargins(0, 4, 4, 4)
        self._legend_layout.setSpacing(8)
        self._legend_layout.addStretch(1)
        legend_container = QWidget()
        legend_container.setLayout(self._legend_layout)
        legend_container.setFixedWidth(180)
        layout.addWidget(legend_container)

    def set_plan(self, plan: NightPlan | NightPlanForBestRig, local_tz) -> None:
        self.canvas.set_plan(plan)
        self._rebuild_legend(plan, local_tz)

    def _rebuild_legend(self, plan: NightPlan | NightPlanForBestRig, local_tz) -> None:
        while self._legend_layout.count() > 1:
            item = self._legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rows = data_adapter.build_shortlist_rows(plan, local_tz)
        for row in rows:
            self._legend_layout.insertWidget(self._legend_layout.count() - 1, self._legend_row(row))

    @staticmethod
    def _legend_row(row: data_adapter.ShortlistRow) -> QWidget:
        container = QWidget()
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(
            f"background: {SKY_COLORS[_VERDICT_SKY_KEY[row.verdict_level]]}; border-radius: 5px;"
        )
        row_layout.addWidget(dot)

        name = QLabel(row.label)
        name.setWordWrap(True)
        name.setStyleSheet(f"color: {SKY_COLORS['star']}; font-size: 11px; background: transparent;")
        row_layout.addWidget(name, stretch=1)
        return container

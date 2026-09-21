"""Tonight's polar sky chart — QPainter-rendered, reusing `charting.py`'s
pure alt/az projection geometry and chrome palette (the same module
`lotse plan --chart`'s matplotlib PNG export uses). No new astronomy
here, same as that module.

Light `theme.COLORS['paper']` background, matching every other tab's
content surface — not a permanently-dark "night sky" canvas. Each
track's line is colored by verdict (GO/MARGINAL/SKIP, `theme.
VERDICT_COLORS` — the same colors the Shortlist tab's own Verdict
column uses), while each entry's best-time dot gets its own color from
`charting.SHORTLIST_PALETTE` (the same categorical, CVD-safe palette
the CLI's PNG export uses) so overlapping tracks with the same verdict
still resolve to a distinct target via the legend.

The Moon gets its own thin black track (`charting.moon_track`, backed by
`engine.ephemeris.moon_altaz_series` — a real solar-system body, not a
fixed `Star` the way catalog targets are) plus a small phase icon drawn
at its highest point in the window, shaded to the Moon's real phase
angle (`engine.ephemeris.moon_phase_angle_deg`, not just illumination
fraction — see `_moon_phase_path`'s own docstring for why that
distinction matters). No fabricated astronomy either way (Guiding
principle, CLAUDE.md): both come from skyfield, not an approximation.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from nachtlotse import charting
from nachtlotse.engine import ephemeris
from nachtlotse.gui import data_adapter
from nachtlotse.gui.theme import COLORS, VERDICT_COLORS, RoundedCard
from nachtlotse.planning import NightPlan, NightPlanForBestRig

# Chart-space coordinates from `charting.project()` range roughly -98..98
# (the rim sits at r=90, compass labels a touch further out) — this is
# the half-extent used to scale into pixels.
_CHART_HALF_EXTENT = 100.0


def _track_color(index: int) -> QColor:
    """Entry `index`'s color, cycling through `charting.SHORTLIST_PALETTE`
    (5 slots — `planning.SHORTLIST_SIZE` — so a full shortlist never
    repeats a color; cycling is just a safety net, not the common case)."""
    hex_value = charting.SHORTLIST_PALETTE[index % len(charting.SHORTLIST_PALETTE)]
    return QColor(hex_value)


def _verdict_line_color(level: str) -> QColor:
    """The same foreground color `VerdictBadge` uses for that verdict's
    text — legible on the chart's light `paper` background, and already
    the color a viewer associates with GO/MARGINAL/SKIP elsewhere."""
    fg, _bg = VERDICT_COLORS[level]
    return QColor(fg)


def _moon_phase_path(cx: float, cy: float, r: float, phase_angle_deg: float) -> QPainterPath:
    """The outline of the Moon's *illuminated* region for a small phase
    icon, given the real phase angle (`ephemeris.moon_phase_angle_deg`:
    0° new, 180° full, waxing 0-180°, waning 180-360°) — not just an
    illumination fraction, which alone can't say which side is lit.

    Built from two known facts about the terminator (the light/dark
    boundary): it's always a half-ellipse against a half-circle, and its
    horizontal radius is `r * |cos(phase_angle)|` (0 at first/last
    quarter, growing to `r` — a full half-circle, i.e. coinciding with
    the limb — at new and full). Below half lit (crescent): subtract the
    terminator ellipse from the lit half-disk. Above half lit (gibbous):
    add it instead. Verified by rendering all 8 principal phases and
    checking the crescent/gibbous shapes and left/right sides by eye,
    not just by this reasoning on paper.
    """
    theta_deg = phase_angle_deg % 360.0
    theta = math.radians(theta_deg)
    terminator_rx = r * abs(math.cos(theta))

    full_disk = QPainterPath()
    full_disk.addEllipse(QPointF(cx, cy), r, r)

    lit_side_rect = QPainterPath()
    if theta_deg < 180.0:  # waxing: lit on the right
        lit_side_rect.addRect(cx, cy - r, r, 2 * r)
    else:  # waning: lit on the left
        lit_side_rect.addRect(cx - r, cy - r, r, 2 * r)
    lit_half_disk = full_disk.intersected(lit_side_rect)

    terminator_disk = QPainterPath()
    terminator_disk.addEllipse(QPointF(cx, cy), terminator_rx, r)

    if math.cos(theta) > 0:  # less than half lit
        return lit_half_disk.subtracted(terminator_disk)
    return lit_half_disk.united(terminator_disk).intersected(full_disk)


class SkyChartCanvas(QWidget):
    """Paints the polar chart for whatever plan was last staged via
    `set_plan` — nothing is drawn until a plan with a non-empty
    shortlist arrives.

    Kept square and pinned to the card's left edge: vertical size policy
    is Expanding (fills the card's height, same as any QHBoxLayout
    child), horizontal is Fixed — `resizeEvent` locks the width to match
    the height on every resize (capped at `_MAX_SIZE`, so a tall window
    doesn't inflate the chart far past a readable size), so the drawing
    (already computed from `min(width, height)`, see `paintEvent`) never
    sits in a canvas wider than it needs, and the legend column gets
    that leftover width instead of empty card background.
    """

    _MAX_SIZE = 460

    def __init__(self) -> None:
        super().__init__()
        self._plan: NightPlan | NightPlanForBestRig | None = None
        self.setMinimumSize(320, 320)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.setFixedWidth(min(self.height(), self._MAX_SIZE))

    def set_plan(self, plan: NightPlan | NightPlanForBestRig) -> None:
        self._plan = plan
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(COLORS["paper"]))

        if self._plan is None or not self._plan.shortlist:
            painter.setPen(QColor(COLORS["ink_secondary"]))
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
        self._paint_moon(painter, to_px)
        painter.end()

    def _paint_horizon_wedge(self, painter: QPainter, to_px) -> None:
        wedge = charting.horizon_wedge(self._plan.site)
        path = QPainterPath()
        path.moveTo(to_px(wedge[0]))
        for point in wedge[1:]:
            path.lineTo(to_px(point))
        path.closeSubpath()
        fill = QColor(charting.HORIZON_FILL_COLOR)
        fill.setAlphaF(0.5)  # matches chart_export.py's matplotlib alpha
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill)
        painter.drawPath(path)

    def _paint_grid(self, painter: QPainter, to_px) -> None:
        painter.setBrush(Qt.NoBrush)  # else the wedge's leftover fill bleeds into these outlines
        font = QFont()
        font.setPointSizeF(8.0)
        painter.setFont(font)
        pen = QPen(QColor(charting.GRID_COLOR))
        pen.setWidthF(0.75)
        for alt_deg in charting.GRID_RINGS_ALT_DEG:
            ring = [to_px(p) for p in charting.grid_ring(alt_deg)]
            painter.setPen(pen)
            path = QPainterPath()
            path.moveTo(ring[0])
            for point in ring[1:]:
                path.lineTo(point)
            painter.drawPath(path)

            if alt_deg == 0.0:
                continue  # the 0° ring is the rim itself; no separate label
            label_point = to_px(charting.project(alt_deg, az_deg=0.0))
            painter.setPen(QColor(charting.LABEL_COLOR))
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
        painter.setPen(QColor(COLORS["ink"]))
        for label, az_deg in charting.COMPASS_LABELS:
            point = to_px(charting.compass_label_point(az_deg, rim_r=97.0))
            painter.drawText(QRectF(point.x() - 12, point.y() - 10, 24, 20), Qt.AlignCenter, label)

    def _paint_tracks(self, painter: QPainter, to_px) -> None:
        tracks = charting.shortlist_tracks(self._plan)
        for index, track in enumerate(tracks):
            entry = self._plan.shortlist[index]
            line_color = _verdict_line_color(entry.verdict.level)
            dot_color = _track_color(index)
            pen = QPen(line_color)
            pen.setWidthF(1.4)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            # Reset every iteration, not once before the loop: the
            # best-time dot below sets a *fill* brush, and left alone it
            # leaks into the next entry's drawPath() call here, turning
            # a thin stroked line into a filled (and, since these curved
            # paths aren't closed shapes, badly self-overlapping) band —
            # the "crescent" this whole chart was originally reported
            # broken over.
            painter.setBrush(Qt.NoBrush)
            for segment in track.segments:
                if len(segment) < 2:
                    continue
                path = QPainterPath()
                path.moveTo(to_px(segment[0]))
                for point in segment[1:]:
                    path.lineTo(to_px(point))
                painter.drawPath(path)

            # Mark the entry's scored best-time position with a filled dot,
            # in its own per-target color — the line above tells you the
            # verdict, this dot (and the matching legend entry) tells you
            # which target it belongs to.
            ranked = entry.ranked
            best_point = to_px(charting.project(ranked.pos.alt_deg, ranked.pos.az_deg))
            painter.setPen(Qt.NoPen)
            painter.setBrush(dot_color)
            painter.drawEllipse(best_point, 4.0, 4.0)

    def _paint_moon(self, painter: QPainter, to_px) -> None:
        track = charting.moon_track(
            self._plan.site, self._plan.evening_start, self._plan.morning_end
        )
        if not track.segments:
            return  # the Moon never clears the horizon during this window

        pen = QPen(QColor("#000000"))
        pen.setWidthF(1.0)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        # The highest point on the track (smallest distance from center,
        # since chart-space radius is zenith distance — see
        # `charting.project`) stands in for the Moon's "best time" the
        # way each target's own peak does; the Moon has no fit/reach
        # score of its own to rank a single instant by.
        peak_point: tuple[float, float] | None = None
        peak_radius: float | None = None
        for segment in track.segments:
            if len(segment) >= 2:
                path = QPainterPath()
                path.moveTo(to_px(segment[0]))
                for point in segment[1:]:
                    path.lineTo(to_px(point))
                painter.drawPath(path)
            for point in segment:
                radius = math.hypot(*point)
                if peak_radius is None or radius < peak_radius:
                    peak_radius = radius
                    peak_point = point
        if peak_point is None:
            return

        # The phase barely changes across one night (~12-13°/day), so the
        # window's midpoint is a fine, real (not fabricated) reference
        # time for the icon — it doesn't need to be the exact peak moment.
        evening_start = self._plan.evening_start
        morning_end = self._plan.morning_end
        midpoint = evening_start + (morning_end - evening_start) / 2
        phase_angle_deg = ephemeris.moon_phase_angle_deg(midpoint)

        center = to_px(peak_point)
        icon_r = 6.0
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(COLORS["ink_muted"]))
        painter.drawEllipse(center, icon_r, icon_r)
        painter.setBrush(QColor("#f3efe4"))
        painter.drawPath(_moon_phase_path(center.x(), center.y(), icon_r, phase_angle_deg))
        outline_pen = QPen(QColor(COLORS["ink_secondary"]))
        outline_pen.setWidthF(0.8)
        painter.setPen(outline_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, icon_r, icon_r)


class SkyChartCard(RoundedCard):
    """The chart canvas plus a legend column naming each shortlisted
    entry and its track color."""

    def __init__(self) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        # >= RoundedCard's own 16px border-radius: the canvas paints a
        # square fillRect right to its own widget edges (QPainter has no
        # idea the parent frame is rounded), so a smaller margin here
        # lets that square corner visibly poke out past the frame's
        # curve — same bug already fixed on the table cards
        # (main_window._CARD_CONTENT_MARGIN).
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.canvas = SkyChartCanvas()
        # No stretch: the canvas is square (see its own docstring) and
        # takes only the width its Fixed size policy gives it — all
        # leftover horizontal space goes to the legend below instead.
        layout.addWidget(self.canvas)

        self._legend_layout = QVBoxLayout()
        self._legend_layout.setContentsMargins(0, 4, 4, 4)
        self._legend_layout.setSpacing(8)
        self._legend_layout.addStretch(1)
        legend_container = QWidget()
        # Same Qt quirk `theme.label_style` works around for QLabel and
        # main_window._verdict_cell works around for its own container: a
        # plain QWidget with no stylesheet of its own picks up an opaque
        # default-palette background once any stylesheet exists anywhere
        # in the app, instead of staying transparent over the card.
        legend_container.setStyleSheet("background: transparent;")
        legend_container.setLayout(self._legend_layout)
        legend_container.setMinimumWidth(180)
        layout.addWidget(legend_container, stretch=1)

    def set_plan(self, plan: NightPlan | NightPlanForBestRig, local_tz) -> None:
        self.canvas.set_plan(plan)
        self._rebuild_legend(plan, local_tz)

    def _rebuild_legend(self, plan: NightPlan | NightPlanForBestRig, local_tz) -> None:
        while self._legend_layout.count() > 1:
            item = self._legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        rows = data_adapter.build_shortlist_rows(plan, local_tz)
        for index, row in enumerate(rows):
            self._legend_layout.insertWidget(
                self._legend_layout.count() - 1, self._legend_row(row.label, _track_color(index))
            )

        # The Moon is drawn on the canvas (track + phase icon) whenever it
        # clears the horizon during the window — same check `_paint_moon`
        # makes before drawing anything — so the legend should list it too,
        # not just the shortlisted targets, or it's the one thing on the
        # chart nobody can identify.
        moon_track = charting.moon_track(plan.site, plan.evening_start, plan.morning_end)
        if moon_track.segments:
            self._legend_layout.insertWidget(
                self._legend_layout.count() - 1, self._legend_row("Moon", QColor("#000000"))
            )

    @staticmethod
    def _legend_row(label: str, color: QColor) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background: {color.name()}; border-radius: 5px;")
        row_layout.addWidget(dot)

        name = QLabel(label)
        name.setWordWrap(True)
        name.setStyleSheet(f"color: {COLORS['ink']}; font-size: 11px; background: transparent;")
        row_layout.addWidget(name, stretch=1)
        return container

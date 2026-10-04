"""Framing preview window — one plan entry drawn in the rig's frame.

The GUI counterpart of `lotse frame`: the same `engine.framing_preview`
geometry and `frame_export` summary text (via `data_adapter.
build_framing_view`), drawn with QPainter here, like `sky_chart.py`,
rather than through matplotlib. Opened on demand from the Shortlist and
All ranked tables — double-click a row, or select it and press
"Framing preview…".

The sky image is an optional backdrop (see `sky_survey`): the frame
draws immediately, the cutout loads on a background `QThread` (same
reasoning as `main_window._PlanWorker` — a first fetch takes seconds)
and slides in underneath once it arrives. Fetched cutouts are cached on
disk by `sky_survey`, and decoded ones in memory here, so reopening a
target is instant. Without network the preview simply stays without it.

The drawing area is a dark "sky well" in both themes: it holds a
photograph of the night sky, unlike the polar chart's light canvas.
North up, east left, the usual sky-chart orientation.
"""

from __future__ import annotations

import math
from pathlib import Path
from zoneinfo import ZoneInfo

from PySide6.QtCore import QPointF, QRectF, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from nachtlotse import frame_export, sky_survey
from nachtlotse.gui import data_adapter
from nachtlotse.gui import export as gui_export
from nachtlotse.gui.theme import COLORS, RoundedCard, label_style, secondary_button
from nachtlotse.planning import NightPlan

# Decoded cutouts, keyed by request — `sky_survey`'s disk cache saves the
# download, this saves re-decoding the JPEG every time a window reopens.
_IMAGE_CACHE: dict[
    tuple[float, float, float], tuple[sky_survey.SurveyImage, QImage]
] = {}


def _cache_key(view: data_adapter.FramingView) -> tuple[float, float, float]:
    preview = view.preview
    return (
        round(preview.center_ra_deg, 5),
        round(preview.center_dec_deg, 5),
        round(view.cutout_fov_deg, 5),
    )


class _SurveyWorker(QThread):
    """Fetches one cutout off the UI thread (disk cache first)."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, ra_deg: float, dec_deg: float, fov_deg: float) -> None:
        super().__init__()
        self._ra_deg = ra_deg
        self._dec_deg = dec_deg
        self._fov_deg = fov_deg

    def run(self) -> None:
        try:
            image = sky_survey.fetch_cutout_cached(
                self._ra_deg, self._dec_deg, self._fov_deg
            )
        except sky_survey.SurveyImageUnavailable as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(image)


def _draw_anchored_text(
    painter: QPainter, point: QPointF, screen_dx: float, screen_dy: float, text: str
) -> None:
    """Text placed past the end of a line pointing (screen_dx, screen_dy)
    — y up — extending away from it, per `frame_export.text_anchor` (the
    same placement the PNG export uses)."""
    ha, va = frame_export.text_anchor(screen_dx, screen_dy)
    width, height = 120.0, 18.0
    x = {"left": point.x(), "right": point.x() - width}.get(ha, point.x() - width / 2)
    # Qt's y grows downward: "bottom" (text above the point) moves up.
    y = {"bottom": point.y() - height, "top": point.y()}.get(va, point.y() - height / 2)
    h_flag = {"left": Qt.AlignLeft, "right": Qt.AlignRight}.get(ha, Qt.AlignHCenter)
    v_flag = {"bottom": Qt.AlignBottom, "top": Qt.AlignTop}.get(va, Qt.AlignVCenter)
    painter.drawText(QRectF(x, y, width, height), h_flag | v_flag, text)


class FramingCanvas(QWidget):
    """Paints a `FramingView`, optionally over a decoded survey image."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(420, 420)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._view: data_adapter.FramingView | None = None
        self._image: sky_survey.SurveyImage | None = None
        self._qimage: QImage | None = None

    def set_view(self, view: data_adapter.FramingView) -> None:
        self._view = view
        self._image = None
        self._qimage = None
        self.update()

    def set_image(self, image: sky_survey.SurveyImage, qimage: QImage) -> None:
        self._image = image
        self._qimage = qimage
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(frame_export.BACKGROUND_COLOR))
        if self._view is None:
            return

        preview = self._view.preview
        half = frame_export.view_half_width_arcmin(preview, self._image)
        side = min(self.width(), self.height())
        scale = side / (2.0 * half)
        cx = self.width() / 2.0
        cy = self.height() / 2.0

        def to_px(east_arcmin: float, north_arcmin: float) -> QPointF:
            # East left, north up.
            return QPointF(cx - east_arcmin * scale, cy - north_arcmin * scale)

        if self._qimage is not None:
            painter.drawImage(
                QRectF(cx - side / 2.0, cy - side / 2.0, side, side), self._qimage
            )

        self._paint_orientation_ring(painter, to_px, scale, half)
        self._paint_frame(painter, to_px, half)
        self._paint_objects(painter, to_px, scale, half)
        self._paint_chrome(painter, to_px, half, scale)

    def _paint_frame(self, painter: QPainter, to_px, half: float) -> None:
        preview = self._view.preview
        pen = QPen(QColor(frame_export.FRAME_COLOR), 2.0)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPolygon(QPolygonF([to_px(*c) for c in preview.frame_corners]))

        if preview.rotation_rate_deg_per_min is None:
            return
        # A short arrow off the frame's top edge, toward the zenith.
        angle_rad = math.radians(preview.frame_angle_deg)
        up = (math.sin(angle_rad), math.cos(angle_rad))
        edge = preview.fov_height_arcmin / 2.0
        length = half * 0.08
        start = to_px(up[0] * edge, up[1] * edge)
        tip = to_px(up[0] * (edge + length), up[1] * (edge + length))
        painter.drawLine(start, tip)
        direction = tip - start
        norm = math.hypot(direction.x(), direction.y()) or 1.0
        ux, uy = direction.x() / norm, direction.y() / norm
        head = 7.0
        painter.setBrush(QColor(frame_export.FRAME_COLOR))
        painter.drawPolygon(
            QPolygonF(
                [
                    tip,
                    QPointF(
                        tip.x() - ux * head - uy * head * 0.6,
                        tip.y() - uy * head + ux * head * 0.6,
                    ),
                    QPointF(
                        tip.x() - ux * head + uy * head * 0.6,
                        tip.y() - uy * head - ux * head * 0.6,
                    ),
                ]
            )
        )
        painter.setFont(QFont(painter.font().family(), 10))
        label_at = to_px(up[0] * (edge + length * 1.2), up[1] * (edge + length * 1.2))
        when_text = preview.when.astimezone(self._view.local_tz)
        _draw_anchored_text(
            painter, label_at, -up[0], up[1], f"zenith {when_text:%H:%M}"
        )

    def _paint_orientation_ring(
        self, painter: QPainter, to_px, scale: float, half: float
    ) -> None:
        """Hourly "up" directions across the night (see
        `engine.framing_preview.orientation_track`) as ticks on a faint
        ring just outside the frame's corners; the drawn moment's tick in
        the frame color."""
        preview = self._view.preview
        ticks = frame_export.orientation_ticks(preview, self._view.local_tz)
        if not ticks:
            return
        ring = frame_export.orientation_ring_radius_arcmin(preview)
        chrome = QColor(frame_export.CHROME_COLOR)
        faint = QColor(chrome)
        faint.setAlpha(90)
        painter.setPen(QPen(faint, 0.8))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(to_px(0.0, 0.0), ring * scale, ring * scale)

        painter.setFont(QFont(painter.font().family(), 9))
        tick_length = half * 0.035
        for tick in ticks:
            angle_rad = math.radians(tick.angle_deg)
            up = (math.sin(angle_rad), math.cos(angle_rad))
            outer = ring + tick_length * (1.6 if tick.highlight else 1.0)
            color = QColor(frame_export.FRAME_COLOR) if tick.highlight else chrome
            painter.setPen(QPen(color, 2.4 if tick.highlight else 1.3))
            painter.drawLine(
                to_px(up[0] * ring, up[1] * ring), to_px(up[0] * outer, up[1] * outer)
            )
            if tick.label:
                painter.setPen(chrome)
                label_r = outer + tick_length * 0.3
                _draw_anchored_text(
                    painter,
                    to_px(up[0] * label_r, up[1] * label_r),
                    -up[0],
                    up[1],
                    tick.label,
                )

    def _paint_objects(
        self, painter: QPainter, to_px, scale: float, half: float
    ) -> None:
        bold = QFont(painter.font().family(), 11)
        bold.setBold(True)
        plain = QFont(painter.font().family(), 10)
        painter.setBrush(Qt.NoBrush)
        below = frame_export.labels_below(self._view.preview)
        for obj in self._view.preview.objects:
            color = QColor(
                frame_export.PRIMARY_COLOR
                if obj.primary
                else frame_export.NEIGHBOR_COLOR
            )
            center = to_px(obj.east_arcmin, obj.north_arcmin)
            if obj.size_known:
                # No position angle in the catalog — the major axis as a
                # circle, the object's reach rather than its shape (same
                # as the PNG export).
                radius_px = obj.target.size_arcmin[0] / 2.0 * scale
                pen = QPen(color, 1.4 if obj.primary else 1.0, Qt.DashLine)
                painter.setPen(pen)
                painter.drawEllipse(center, radius_px, radius_px)
            else:
                radius_px = half * 0.03 * scale
                painter.setPen(QPen(color, 1.4))
                painter.drawLine(
                    QPointF(center.x() - radius_px, center.y()),
                    QPointF(center.x() + radius_px, center.y()),
                )
                painter.drawLine(
                    QPointF(center.x(), center.y() - radius_px),
                    QPointF(center.x(), center.y() + radius_px),
                )
            painter.setPen(color)
            painter.setFont(bold if obj.primary else plain)
            label = obj.target.catalog_id or obj.target.name
            if below:
                label_rect = QRectF(
                    center.x() - 80, center.y() + radius_px + 2, 160, 18
                )
            else:
                label_rect = QRectF(
                    center.x() - 80, center.y() - radius_px - 20, 160, 18
                )
            painter.drawText(label_rect, Qt.AlignCenter, label)

    def _paint_chrome(
        self, painter: QPainter, to_px, half: float, scale: float
    ) -> None:
        chrome = QColor(frame_export.CHROME_COLOR)
        painter.setPen(QPen(chrome, 1.2))
        painter.setFont(QFont(painter.font().family(), 10))

        # Compass (lower left): N up, E left.
        origin = to_px(half * 0.82, -half * 0.82)
        arm = half * 0.1 * scale
        north_tip = QPointF(origin.x(), origin.y() - arm)
        east_tip = QPointF(origin.x() - arm, origin.y())
        painter.drawLine(origin, north_tip)
        painter.drawLine(origin, east_tip)
        painter.drawText(
            QRectF(north_tip.x() - 10, north_tip.y() - 20, 20, 18), Qt.AlignCenter, "N"
        )
        painter.drawText(
            QRectF(east_tip.x() - 22, east_tip.y() - 9, 20, 18), Qt.AlignCenter, "E"
        )

        # Scale bar (lower right).
        bar_arcmin = frame_export.scale_bar_arcmin(half)
        right = to_px(-half * 0.85, -half * 0.9)
        left = QPointF(right.x() - bar_arcmin * scale, right.y())
        painter.setPen(QPen(chrome, 2.0))
        painter.drawLine(left, right)
        painter.drawText(
            QRectF(left.x(), left.y() - 22, right.x() - left.x(), 18),
            Qt.AlignCenter,
            frame_export.format_angle_arcmin(bar_arcmin),
        )


class FramingWindow(QDialog):
    """Non-modal: it stays open next to the main window, and selecting
    another row and asking again replaces its content."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Framing preview")
        self.setModal(False)
        self.resize(760, 900)
        self.setStyleSheet(f"QDialog {{ background: {COLORS['cream']}; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        card = RoundedCard()
        outer.addWidget(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        self._title = QLabel()
        self._title.setWordWrap(True)
        self._title.setStyleSheet(
            label_style(f"color: {COLORS['ink']}; font-size: 18px; font-weight: 500;")
        )
        layout.addWidget(self._title)

        self.canvas = FramingCanvas()
        layout.addWidget(self.canvas, stretch=1)

        self._summary = QLabel()
        self._summary.setWordWrap(True)
        self._summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._summary.setStyleSheet(
            label_style(f"color: {COLORS['ink']}; font-size: 12px;")
        )
        layout.addWidget(self._summary)

        self._status = QLabel()
        self._status.setWordWrap(True)
        self._status.setStyleSheet(
            label_style(f"color: {COLORS['ink_secondary']}; font-size: 11px;")
        )
        layout.addWidget(self._status)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self._export_button = secondary_button("Export PNG…")
        self._export_button.clicked.connect(self._on_export_clicked)
        button_row.addWidget(self._export_button)
        layout.addLayout(button_row)

        self._view: data_adapter.FramingView | None = None
        self._image: sky_survey.SurveyImage | None = None
        # Workers still running for an entry since replaced keep a
        # reference here until they finish (a QThread must not be
        # garbage-collected mid-run); their results are ignored.
        self._workers: set[_SurveyWorker] = set()
        self._request_id = 0

    def show_entry(self, plan: NightPlan, ranked: object, local_tz: ZoneInfo) -> None:
        view = data_adapter.build_framing_view(plan, ranked, local_tz)
        self._view = view
        self._image = None
        self._request_id += 1

        self._title.setText(view.title)
        self._summary.setText("\n".join(view.summary_lines))
        self.canvas.set_view(view)

        cached = _IMAGE_CACHE.get(_cache_key(view))
        if cached is not None:
            self._show_image(*cached)
        else:
            self._status.setText(f"Loading sky image…  ·  {frame_export.CIRCLE_NOTE}")
            self._start_worker(view, self._request_id)

        self.show()
        self.raise_()
        self.activateWindow()

    def _start_worker(self, view: data_adapter.FramingView, request_id: int) -> None:
        preview = view.preview
        worker = _SurveyWorker(
            preview.center_ra_deg, preview.center_dec_deg, view.cutout_fov_deg
        )
        key = _cache_key(view)
        worker.succeeded.connect(
            lambda image: self._on_image_ready(image, key, request_id)
        )
        worker.failed.connect(lambda _message: self._on_image_failed(request_id))
        worker.finished.connect(lambda: self._workers.discard(worker))
        self._workers.add(worker)
        worker.start()

    def _on_image_ready(
        self,
        image: sky_survey.SurveyImage,
        key: tuple[float, float, float],
        request_id: int,
    ) -> None:
        qimage = QImage.fromData(image.jpeg_bytes, "JPG")
        if qimage.isNull():
            self._on_image_failed(request_id)
            return
        _IMAGE_CACHE[key] = (image, qimage)
        if request_id == self._request_id:
            self._show_image(image, qimage)

    def _show_image(self, image: sky_survey.SurveyImage, qimage: QImage) -> None:
        self._image = image
        self.canvas.set_image(image, qimage)
        self._status.setText(
            f"Sky image: {image.credit}  ·  {frame_export.CIRCLE_NOTE}"
        )

    def _on_image_failed(self, request_id: int) -> None:
        if request_id != self._request_id:
            return
        self._status.setText(
            "Sky image unavailable (offline or hips2fits unreachable) — "
            f"drawn without it  ·  {frame_export.CIRCLE_NOTE}"
        )

    def _on_export_clicked(self) -> None:
        view = self._view
        if view is None:
            return
        default_path = str(
            gui_export.default_export_dir()
            / frame_export.default_filename(view.targets)
        )
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Export Framing Preview", default_path, "PNG images (*.png)"
        )
        if not path_str:
            return
        try:
            frame_export.save_framing_preview(
                view.preview,
                Path(path_str),
                title=view.title,
                caption_lines=view.summary_lines,
                image=self._image,
                local_tz=view.local_tz,
            )
        except (frame_export.FrameExportUnavailable, OSError) as exc:
            QMessageBox.critical(self, "Export failed", str(exc))

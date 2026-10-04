"""Smoke tests for the framing preview window (nachtlotse/gui/framing_view.py).

Real Qt widgets on the offscreen platform — skipped without the `gui`
extra. They check that the window fills in from a plan entry and that the
canvas paints with and without a sky image; what it draws is the engine's
geometry, tested in test_framing_preview.py.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from nachtlotse import sky_survey
from nachtlotse.gui import framing_view
from nachtlotse.planning import RankedTarget
from tests.test_gui_data_adapter import (
    _TARGET_A,
    _WHEN,
    BERLIN,
    _night_plan,
    _pos,
)


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _wait_for_workers(window: framing_view.FramingWindow, app: QApplication) -> None:
    for worker in list(window._workers):
        worker.wait(5000)
    app.processEvents()


def _jpeg_bytes() -> bytes:
    image = QImage(64, 64, QImage.Format_RGB32)
    image.fill(QColor(20, 30, 60))
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "JPG")
    return bytes(buffer.data())


def test_window_shows_the_entry_and_falls_back_without_a_sky_image(
    qapp: QApplication,
) -> None:
    framing_view._IMAGE_CACHE.clear()
    ranked = RankedTarget(_TARGET_A, _WHEN, _pos(60.0, 90.0), 1.0, 1.0)
    window = framing_view.FramingWindow()
    window.show_entry(_night_plan([ranked]), ranked, BERLIN)
    _wait_for_workers(window, qapp)  # the suite is offline (see conftest)

    assert window._title.text().startswith("TA1 target a — Test Rig · ")
    assert window._summary.text().startswith("Frame: ")
    assert "Sky image unavailable" in window._status.text()
    assert not window.canvas.grab().isNull()
    window.close()


def test_canvas_paints_over_a_cached_sky_image(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    framing_view._IMAGE_CACHE.clear()
    jpeg = _jpeg_bytes()
    monkeypatch.setattr(
        sky_survey,
        "fetch_cutout",
        lambda ra, dec, fov, **_: sky_survey.SurveyImage(
            jpeg, ra, dec, fov, 64, sky_survey.DEFAULT_SURVEY
        ),
    )
    ranked = RankedTarget(_TARGET_A, _WHEN, _pos(60.0, 90.0), 1.0, 1.0)
    window = framing_view.FramingWindow()
    window.show_entry(_night_plan([ranked]), ranked, BERLIN)
    _wait_for_workers(window, qapp)

    assert "DSS2" in window._status.text()
    assert window._image is not None
    assert len(framing_view._IMAGE_CACHE) == 1
    pixmap = window.canvas.grab()
    # The cutout's dark blue shows through where nothing else is drawn.
    corner = pixmap.toImage().pixelColor(pixmap.width() // 2, 5)
    assert corner.blue() > corner.red()

    # Reopening serves the decoded image from memory — no new worker.
    window.show_entry(_night_plan([ranked]), ranked, BERLIN)
    assert not window._workers
    assert window._image is not None
    window.close()

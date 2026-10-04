"""Tests for `lotse frame`'s text summary and PNG export
(nachtlotse/frame_export.py).

Like test_chart_export.py: the "matplotlib missing" path is forced via the
import seam; rendering tests need the real library (the `charts` extra)
and skip otherwise.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from nachtlotse import frame_export, sky_survey
from nachtlotse.engine import framing_preview
from nachtlotse.engine.models import Target
from tests.test_framing import ALTAZ_RIG, EQ_RIG, SITE
from tests.test_framing_preview import M31, M32, M42, M110

WHEN = datetime(2026, 9, 12, 21, 0, tzinfo=UTC)
BERLIN = ZoneInfo("Europe/Berlin")


def _preview(rig=ALTAZ_RIG, targets=(M31,), neighbors=(M32, M110)):
    return framing_preview.framing_preview(
        SITE, rig, targets, WHEN, neighbors=neighbors
    )


def test_default_filename_joins_catalog_ids_without_spaces() -> None:
    assert frame_export.default_filename([M31]) == "nachtlotse-frame-M31.png"
    ngc = Target(name="x", catalog_id="NGC 224", ra_deg=0, dec_deg=0)
    assert (
        frame_export.default_filename([M31, ngc]) == "nachtlotse-frame-M31+NGC224.png"
    )


def test_summary_lines_for_an_altaz_single_target() -> None:
    preview = _preview()
    text = "\n".join(frame_export.summary_lines(preview, ALTAZ_RIG, [M31], BERLIN))

    assert f"{preview.fill_fraction * 100:.0f}% of the frame's short side" in text
    assert f"fit {preview.fit:.2f}" in text
    assert "3.2° × 1.0°" in text  # one unit for both axes
    assert f"{preview.frame_angle_deg:+.0f}° (N through E)" in text
    assert f"{preview.rotation_rate_deg_per_min:.2f}°/min" in text
    assert "23:00 CEST" in text  # local time at the UI boundary
    assert "Also in frame: M32, M110" in text


def test_summary_lines_for_an_eq_mount_has_no_rotation() -> None:
    text = "\n".join(
        frame_export.summary_lines(_preview(rig=EQ_RIG), EQ_RIG, [M31], BERLIN)
    )
    assert "no field rotation" in text
    assert "°/min" not in text


def test_summary_lines_for_a_group_and_an_unknown_size() -> None:
    group = "\n".join(
        frame_export.summary_lines(
            _preview(targets=(M31, M110), neighbors=()), ALTAZ_RIG, [M31, M110], BERLIN
        )
    )
    assert "Group span" in group
    assert "Also in frame" not in group

    unknown = "\n".join(
        frame_export.summary_lines(
            _preview(targets=(M42,), neighbors=()), ALTAZ_RIG, [M42], BERLIN
        )
    )
    assert "Size: unknown" in unknown


def test_save_raises_when_matplotlib_is_unavailable(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    def _boom():
        raise ImportError("simulated: matplotlib not installed")

    monkeypatch.setattr(frame_export, "_import_matplotlib", _boom)
    with pytest.raises(frame_export.FrameExportUnavailable, match="charts"):
        frame_export.save_framing_preview(
            _preview(), tmp_path / "out.png", title="t", caption_lines=[]
        )


def test_save_writes_a_png_without_a_sky_image(tmp_path) -> None:
    pytest.importorskip("matplotlib")
    path = tmp_path / "frame.png"
    frame_export.save_framing_preview(
        _preview(), path, title="M31", caption_lines=["line"]
    )
    assert path.read_bytes().startswith(b"\x89PNG")


def test_save_writes_a_png_over_a_sky_image(tmp_path) -> None:
    pytest.importorskip("matplotlib")
    from PIL import Image  # a matplotlib dependency

    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), (10, 20, 30)).save(buffer, format="JPEG")
    image = sky_survey.SurveyImage(
        buffer.getvalue(), M31.ra_deg, M31.dec_deg, 5.0, 64, sky_survey.DEFAULT_SURVEY
    )
    path = tmp_path / "frame.png"
    frame_export.save_framing_preview(
        _preview(), path, title="M31", caption_lines=["line"], image=image
    )
    assert path.read_bytes().startswith(b"\x89PNG")

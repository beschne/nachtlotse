"""Tests for `lotse frame`'s text summary and PNG export
(nachtlotse/frame_export.py).

Like test_chart_export.py: the "matplotlib missing" path is forced via the
import seam; rendering tests need the real library (the `charts` extra)
and skip otherwise.
"""

from __future__ import annotations

import dataclasses
import io
import math
from datetime import UTC, datetime, timedelta
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


def test_labels_go_above_when_the_zenith_arrow_points_down() -> None:
    preview = _preview()
    flipped = dataclasses.replace(preview, frame_angle_deg=172.0)
    assert frame_export.labels_below(
        dataclasses.replace(preview, frame_angle_deg=-20.0)
    )
    assert not frame_export.labels_below(flipped)
    # Eq mounts draw no zenith arrow at all.
    assert frame_export.labels_below(_preview(rig=EQ_RIG))


def _track(*angles_deg: float) -> tuple[framing_preview.FrameOrientation, ...]:
    start = datetime(2026, 9, 12, 21, 0, tzinfo=UTC)  # 23:00 CEST
    return tuple(
        framing_preview.FrameOrientation(start + timedelta(hours=i), angle, 45.0)
        for i, angle in enumerate(angles_deg)
    )


def test_preview_title_names_the_moment_drawn() -> None:
    title = frame_export.preview_title([M31, M32], ALTAZ_RIG, _preview(), BERLIN)
    assert title == (
        f"M31 Andromeda Galaxy + M32 M32 — {ALTAZ_RIG.name} · Sat 12 Sep, 23:00 CEST"
    )


def test_orientation_ticks_label_each_hour_plus_the_drawn_moment() -> None:
    preview = dataclasses.replace(_preview(), orientation_track=_track(-60, -30, 0))
    ticks = frame_export.orientation_ticks(preview, BERLIN)

    assert [t.label for t in ticks] == ["23", "00", "01", ""]
    assert [t.angle_deg for t in ticks[:3]] == [-60, -30, 0]
    assert ticks[-1].highlight
    assert ticks[-1].angle_deg == preview.frame_angle_deg


def test_orientation_ticks_merge_crowded_hours_under_one_label() -> None:
    preview = dataclasses.replace(
        _preview(), orientation_track=_track(-44, -43, -40, 0)
    )
    labels = [t.label for t in frame_export.orientation_ticks(preview, BERLIN)]
    # 23-01 lie within a few degrees: one label at the middle tick.
    assert labels == ["", "23–01", "", "02", ""]


def test_orientation_ticks_empty_without_a_track() -> None:
    assert frame_export.orientation_ticks(_preview(), BERLIN) == []
    assert frame_export.orientation_ticks(_preview(rig=EQ_RIG), BERLIN) == []


def test_summary_lines_describe_the_night() -> None:
    preview = dataclasses.replace(_preview(), orientation_track=_track(-60, -30, 0))
    text = "\n".join(frame_export.summary_lines(preview, ALTAZ_RIG, [M31], BERLIN))
    assert "Through the night: -60° at 23:00 → +0° at 01:00" in text


@pytest.mark.parametrize(
    ("dx", "dy", "expected"),
    [
        (1.0, 0.0, ("left", "center")),
        (-1.0, 0.0, ("right", "center")),
        (0.0, 1.0, ("center", "bottom")),
        (0.0, -1.0, ("center", "top")),
    ],
)
def test_text_anchor_extends_labels_away_from_their_line(dx, dy, expected) -> None:
    assert frame_export.text_anchor(dx, dy) == expected


def test_ring_sits_outside_the_frame_corners_and_inside_the_view() -> None:
    preview = _preview()
    corner_arcmin = max(math.hypot(*c) for c in preview.frame_corners)
    ring = frame_export.orientation_ring_radius_arcmin(preview)
    assert corner_arcmin < ring < frame_export.view_half_width_arcmin(preview, None)


def test_a_neighbor_next_to_the_target_labels_on_the_other_side() -> None:
    from nachtlotse.engine.framing_preview import FramedObject

    preview = _preview(rig=EQ_RIG)  # labels below by default
    half = frame_export.view_half_width_arcmin(preview, None)
    target = next(o for o in preview.objects if o.primary)
    host = FramedObject(M110, target.east_arcmin + 1.0, target.north_arcmin, False)
    far = FramedObject(M110, target.east_arcmin + half / 2, target.north_arcmin, False)
    assert frame_export.label_below(preview, target, half)
    assert not frame_export.label_below(preview, host, half)
    assert frame_export.label_below(preview, far, half)


def test_summary_calls_a_supernova_a_point_source() -> None:
    supernova = framing_preview.Target(
        name="SN 2026aaiv", ra_deg=339.2735, dec_deg=34.4098, types=("supernova",)
    )
    preview = framing_preview.framing_preview(SITE, ALTAZ_RIG, [supernova], WHEN)
    text = "\n".join(
        frame_export.summary_lines(preview, ALTAZ_RIG, [supernova], BERLIN)
    )
    assert "Point source (supernova) — fits any frame" in text

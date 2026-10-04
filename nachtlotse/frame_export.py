"""PNG export of a framing preview, for `lotse frame`.

Draws `engine.framing_preview`'s geometry — the rig's frame, the
target(s), catalog neighbors inside the frame — optionally on top of a
`sky_survey` cutout. Every number on the image comes from the engine;
the cutout is only a backdrop.

matplotlib is the same optional `charts` extra `chart_export.py` uses,
imported lazily inside `save_framing_preview` so `cli.py` never needs it
just to run other commands. `summary_lines` has no matplotlib dependency
at all and is shared by the CLI's text output and the PNG's caption.

Sky charts are drawn north up, east left — the x axis is inverted, so
`east_arcmin` values plot straight through.
"""

from __future__ import annotations

import io
import math
from collections.abc import Sequence
from datetime import tzinfo
from pathlib import Path

from nachtlotse import sky_survey
from nachtlotse.engine.framing_preview import FramingPreview
from nachtlotse.engine.models import Rig, Target

_BACKGROUND_COLOR = "#0b0d12"
_FRAME_COLOR = "#f5b83d"
_PRIMARY_COLOR = "#ffffff"
_NEIGHBOR_COLOR = "#a9b4c2"
_CHROME_COLOR = "#c3c2b7"

# Scale-bar lengths to choose from, in arcmin — the longest that stays
# within ~a quarter of the view wins.
_SCALE_BAR_CHOICES_ARCMIN = (1.0, 2.0, 5.0, 10.0, 15.0, 30.0, 60.0, 120.0, 180.0)


class FrameExportUnavailable(Exception):
    """The `charts` extra (matplotlib) isn't installed."""


def default_filename(targets: Sequence[Target]) -> str:
    """e.g. "nachtlotse-frame-M31.png", "nachtlotse-frame-M81+M82.png"."""
    slug = "+".join("".join((t.catalog_id or t.name).split()) for t in targets).replace(
        "/", "-"
    )
    return f"nachtlotse-frame-{slug}.png"


def _format_angle_arcmin(value_arcmin: float, *, degrees: bool | None = None) -> str:
    """Degrees from 2° up (or when forced), arcmin below."""
    if degrees if degrees is not None else value_arcmin >= 120.0:
        return f"{value_arcmin / 60.0:.1f}°"
    return f"{value_arcmin:.0f}′" if value_arcmin >= 10.0 else f"{value_arcmin:.1f}′"


def _format_size(target: Target) -> str:
    """Both axes in the same unit, picked by the major axis."""
    major, minor = target.size_arcmin
    in_degrees = major >= 120.0
    return (
        f"{_format_angle_arcmin(major, degrees=in_degrees)} × "
        f"{_format_angle_arcmin(minor, degrees=in_degrees)}"
    )


def summary_lines(
    preview: FramingPreview, rig: Rig, targets: Sequence[Target], local_tz: tzinfo
) -> list[str]:
    """The preview's numbers as plain text lines — framing, orientation,
    and what else lands in the frame."""
    lines = [
        f"Frame: {preview.fov_width_arcmin / 60.0:.2f}° × "
        + f"{preview.fov_height_arcmin / 60.0:.2f}° · {rig.name}"
    ]

    if preview.fill_fraction is None:
        lines.append("Size: unknown — framing fit not constrained")
    else:
        what = (
            f"Target {_format_size(targets[0])}"
            if len(targets) == 1
            else f"Group span {_format_angle_arcmin(preview.span_arcmin)}"
        )
        lines.append(
            f"{what} · {preview.fill_fraction * 100:.0f}% of the frame's "
            f"short side · fit {preview.fit:.2f}"
        )

    local_time = preview.when.astimezone(local_tz)
    if preview.rotation_rate_deg_per_min is None:
        lines.append("Orientation: long side east–west (eq mount, no field rotation)")
    else:
        lines.append(
            f"Orientation at {local_time:%H:%M %Z}: frame top toward the zenith at "
            f"{preview.frame_angle_deg:+.0f}° (N through E) · rotating "
            f"{preview.rotation_rate_deg_per_min:.2f}°/min"
        )

    neighbors = [obj.target for obj in preview.objects if not obj.primary]
    if neighbors:
        lines.append(
            "Also in frame: " + ", ".join(t.catalog_id or t.name for t in neighbors)
        )
    return lines


def _import_matplotlib():
    """The lazy-import seam, factored out so tests can force the
    "matplotlib missing" path without needing to actually uninstall it."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyArrowPatch, Polygon

    return plt, Circle, FancyArrowPatch, Polygon


def _scale_bar_arcmin(view_half_arcmin: float) -> float:
    fitting = [c for c in _SCALE_BAR_CHOICES_ARCMIN if c <= view_half_arcmin / 2.0]
    return fitting[-1] if fitting else _SCALE_BAR_CHOICES_ARCMIN[0]


def save_framing_preview(
    preview: FramingPreview,
    path: Path,
    *,
    title: str,
    caption_lines: Sequence[str],
    image: sky_survey.SurveyImage | None = None,
) -> None:
    """Render `preview` as a PNG to `path`, overwriting whatever was
    there, with `image` as the backdrop if given. Raises
    `FrameExportUnavailable` if matplotlib isn't installed.
    """
    try:
        plt, Circle, FancyArrowPatch, Polygon = _import_matplotlib()
    except ImportError as exc:
        raise FrameExportUnavailable(
            "PNG export needs matplotlib, which isn't installed — run "
            "`uv sync --extra charts` and try again."
        ) from exc

    if image is not None:
        half = image.half_width_tangent_arcmin
    else:
        cutout_deg = sky_survey.cutout_fov_deg(
            preview.fov_width_arcmin, preview.fov_height_arcmin
        )
        half = math.degrees(math.tan(math.radians(cutout_deg / 2.0))) * 60.0

    fig, ax = plt.subplots(figsize=(7, 7), facecolor=_BACKGROUND_COLOR)
    ax.set_facecolor(_BACKGROUND_COLOR)
    ax.set_aspect("equal")
    # North up, east left: inverted x axis, so east_arcmin plots as-is.
    ax.set_xlim(half, -half)
    ax.set_ylim(-half, half)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    if image is not None:
        pixels = plt.imread(io.BytesIO(image.jpeg_bytes), format="jpg")
        # Row 0 is north, column 0 is east — matches the axes as set.
        ax.imshow(pixels, extent=(half, -half, -half, half), origin="upper", zorder=0)

    ax.add_patch(
        Polygon(
            preview.frame_corners,
            closed=True,
            fill=False,
            edgecolor=_FRAME_COLOR,
            linewidth=2.0,
            zorder=3,
        )
    )
    if preview.rotation_rate_deg_per_min is not None:
        # A short arrow off the frame's top edge, toward the zenith.
        angle_rad = math.radians(preview.frame_angle_deg)
        up = (math.sin(angle_rad), math.cos(angle_rad))
        edge = preview.fov_height_arcmin / 2.0
        length = half * 0.08
        start = (up[0] * edge, up[1] * edge)
        end = (up[0] * (edge + length), up[1] * (edge + length))
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=12,
                color=_FRAME_COLOR,
                linewidth=1.5,
                zorder=3,
            )
        )
        ax.annotate(
            "zenith",
            (end[0] + up[0] * length * 0.4, end[1] + up[1] * length * 0.4),
            color=_FRAME_COLOR,
            fontsize=8,
            ha="center",
            va="center",
            zorder=4,
        )

    for obj in preview.objects:
        color = _PRIMARY_COLOR if obj.primary else _NEIGHBOR_COLOR
        center = (obj.east_arcmin, obj.north_arcmin)
        if obj.size_known:
            # The catalog has no position angle, so the major axis is
            # drawn as a circle — the object's reach, not its shape.
            radius = obj.target.size_arcmin[0] / 2.0
            ax.add_patch(
                Circle(
                    center,
                    radius,
                    fill=False,
                    edgecolor=color,
                    linestyle="--",
                    linewidth=1.2 if obj.primary else 0.8,
                    zorder=2,
                )
            )
            label_offset = radius
        else:
            ax.plot(*center, marker="+", markersize=12, color=color, zorder=2)
            label_offset = half * 0.03
        ax.annotate(
            obj.target.catalog_id or obj.target.name,
            (center[0], center[1] - label_offset),
            xytext=(0, -4),
            textcoords="offset points",
            color=color,
            fontsize=9 if obj.primary else 7.5,
            fontweight="bold" if obj.primary else "normal",
            ha="center",
            va="top",
            zorder=4,
        )

    # Compass (lower left): N up, E left.
    origin = (half * 0.82, -half * 0.82)
    arm = half * 0.1
    for label, (dx, dy) in (("N", (0.0, arm)), ("E", (arm, 0.0))):
        tip = (origin[0] + dx, origin[1] + dy)
        ax.add_patch(
            FancyArrowPatch(
                origin,
                tip,
                arrowstyle="-|>",
                mutation_scale=10,
                color=_CHROME_COLOR,
                linewidth=1.0,
                zorder=4,
            )
        )
        ax.annotate(
            label,
            (origin[0] + dx * 1.35, origin[1] + dy * 1.35),
            color=_CHROME_COLOR,
            fontsize=8,
            ha="center",
            va="center",
            zorder=4,
        )

    # Scale bar (lower right).
    bar = _scale_bar_arcmin(half)
    bar_right = -half * 0.85
    bar_y = -half * 0.9
    ax.plot(
        [bar_right + bar, bar_right],
        [bar_y, bar_y],
        color=_CHROME_COLOR,
        linewidth=2.0,
        zorder=4,
    )
    ax.annotate(
        _format_angle_arcmin(bar),
        (bar_right + bar / 2.0, bar_y),
        xytext=(0, 4),
        textcoords="offset points",
        color=_CHROME_COLOR,
        fontsize=8,
        ha="center",
        va="bottom",
        zorder=4,
    )

    fig.text(
        0.02,
        0.985,
        title,
        color=_PRIMARY_COLOR,
        fontsize=12 if len(title) <= 60 else 10,
        ha="left",
        va="top",
        wrap=True,
    )
    footer = list(caption_lines)
    footer.append(
        f"Sky image: {image.credit}"
        if image is not None
        else "Sky image: none (offline or not requested)"
    )
    footer.append("Dashed circles: catalog major axis (orientation not in catalog)")
    fig.text(
        0.02,
        0.01,
        "\n".join(footer),
        color=_CHROME_COLOR,
        fontsize=8,
        ha="left",
        va="bottom",
        linespacing=1.5,
    )
    fig.subplots_adjust(
        left=0.02, right=0.98, top=0.94, bottom=0.02 + 0.026 * len(footer)
    )
    fig.savefig(path, dpi=150, facecolor=_BACKGROUND_COLOR)
    plt.close(fig)

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
from dataclasses import dataclass
from datetime import UTC, tzinfo
from pathlib import Path

from nachtlotse import sky_survey
from nachtlotse.engine.constraints import DEFAULT_MIN_ALT_DEG
from nachtlotse.engine.framing_preview import FramingPreview
from nachtlotse.engine.models import Rig, Target

BACKGROUND_COLOR = "#0b0d12"
FRAME_COLOR = "#f5b83d"
PRIMARY_COLOR = "#ffffff"
NEIGHBOR_COLOR = "#a9b4c2"
CHROME_COLOR = "#c3c2b7"

# Scale-bar lengths to choose from, in arcmin — the longest that stays
# within ~a quarter of the view wins.
_SCALE_BAR_CHOICES_ARCMIN = (1.0, 2.0, 5.0, 10.0, 15.0, 30.0, 60.0, 120.0, 180.0)


# Shown wherever a preview is drawn (PNG caption, GUI) — the circles are
# a stand-in for shape, see `save_framing_preview`.
CIRCLE_NOTE = "Dashed circles: catalog major axis (orientation not in catalog)"


class FrameExportUnavailable(Exception):
    """The `charts` extra (matplotlib) isn't installed."""


def default_filename(targets: Sequence[Target]) -> str:
    """e.g. "nachtlotse-frame-M31.png", "nachtlotse-frame-M81+M82.png"."""
    slug = "+".join("".join((t.catalog_id or t.name).split()) for t in targets).replace(
        "/", "-"
    )
    return f"nachtlotse-frame-{slug}.png"


def format_angle_arcmin(value_arcmin: float, *, degrees: bool | None = None) -> str:
    """Degrees from 2° up (or when forced), arcmin below."""
    if degrees if degrees is not None else value_arcmin >= 120.0:
        return f"{value_arcmin / 60.0:.1f}°"
    return f"{value_arcmin:.0f}′" if value_arcmin >= 10.0 else f"{value_arcmin:.1f}′"


def _format_size(target: Target) -> str:
    """Both axes in the same unit, picked by the major axis."""
    major, minor = target.size_arcmin
    in_degrees = major >= 120.0
    return (
        f"{format_angle_arcmin(major, degrees=in_degrees)} × "
        f"{format_angle_arcmin(minor, degrees=in_degrees)}"
    )


def preview_title(
    targets: Sequence[Target], rig: Rig, preview: FramingPreview, local_tz: tzinfo
) -> str:
    """e.g. "M31 Andromeda Galaxy — ZWO Seestar S30 Pro · Mon 05 Oct, 01:14
    CEST": the moment drawn belongs in the title, since an alt-az frame
    only looks like this at that time."""
    label = " + ".join(f"{t.catalog_id} {t.name}".strip() for t in targets)
    local_time = preview.when.astimezone(local_tz)
    return f"{label} — {rig.name} · {local_time:%a %d %b, %H:%M %Z}"


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
            else f"Group span {format_angle_arcmin(preview.span_arcmin)}"
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
    track = preview.orientation_track
    if track:
        first, last = track[0], track[-1]
        lines.append(
            f"Through the night: {first.frame_angle_deg:+.0f}° at "
            f"{first.when.astimezone(local_tz):%H:%M} → {last.frame_angle_deg:+.0f}° "
            f"at {last.when.astimezone(local_tz):%H:%M} (ticks: hourly through "
            f"the dark window, altitude ≥ {DEFAULT_MIN_ALT_DEG:.0f}°)"
        )

    neighbors = [obj.target for obj in preview.objects if not obj.primary]
    if neighbors:
        lines.append(
            "Also in frame: " + ", ".join(t.catalog_id or t.name for t in neighbors)
        )
    return lines


def view_half_width_arcmin(
    preview: FramingPreview, image: sky_survey.SurveyImage | None
) -> float:
    """Half the drawn view's width in tangent-plane arcmin: the survey
    image's own extent when there is one, otherwise the extent such an
    image would have — so the layout doesn't jump when it arrives."""
    if image is not None:
        return image.half_width_tangent_arcmin
    cutout_deg = sky_survey.cutout_fov_deg(
        preview.fov_width_arcmin, preview.fov_height_arcmin
    )
    return math.degrees(math.tan(math.radians(cutout_deg / 2.0))) * 60.0


def labels_below(preview: FramingPreview) -> bool:
    """Whether object labels go below their markers — unless the alt-az
    zenith arrow points downward (target north of the zenith), where it
    would run into them; then above."""
    if preview.rotation_rate_deg_per_min is None:
        return True
    return math.cos(math.radians(preview.frame_angle_deg)) >= 0.0


@dataclass(frozen=True)
class OrientationTick:
    """One tick on the orientation ring: the frame's "up" direction (N
    through E) at one moment."""

    angle_deg: float
    label: str
    # The moment the frame itself is drawn for.
    highlight: bool


# Hour ticks closer together than this share one label ("23–01") —
# early or late in the night the angle can barely move per hour.
_TICK_LABEL_MIN_SEPARATION_DEG = 8.0


def orientation_ticks(
    preview: FramingPreview, local_tz: tzinfo
) -> list[OrientationTick]:
    """The ring's ticks: one per `preview.orientation_track` hour, plus an
    unlabeled highlighted one for the drawn moment (its time is on the
    zenith arrow and in the title). Consecutive hours within
    `_TICK_LABEL_MIN_SEPARATION_DEG` of a run's first tick form one run,
    labeled once, at its middle tick, with its first and last hour.
    Empty without a track (eq mount, or no night given)."""
    track = preview.orientation_track
    if not track:
        return []

    runs: list[list[int]] = []
    for index, orientation in enumerate(track):
        if runs:
            first = track[runs[-1][0]].frame_angle_deg
            gap = abs((orientation.frame_angle_deg - first + 180.0) % 360.0 - 180.0)
            if gap < _TICK_LABEL_MIN_SEPARATION_DEG:
                runs[-1].append(index)
                continue
        runs.append([index])

    labels = [""] * len(track)
    for run in runs:
        first_hour = f"{track[run[0]].when.astimezone(local_tz):%H}"
        last_hour = f"{track[run[-1]].when.astimezone(local_tz):%H}"
        labels[run[len(run) // 2]] = (
            first_hour if len(run) == 1 else f"{first_hour}–{last_hour}"
        )

    ticks = [
        OrientationTick(o.frame_angle_deg, label, highlight=False)
        for o, label in zip(track, labels, strict=True)
    ]
    ticks.append(OrientationTick(preview.frame_angle_deg, "", highlight=True))
    return ticks


def orientation_ring_radius_arcmin(preview: FramingPreview) -> float:
    """Just outside the frame's corners, so ticks never cross the frame
    whatever its rotation — and inside the survey cutout, which holds
    the diagonal plus a margin (see `sky_survey.cutout_fov_deg`)."""
    return math.hypot(preview.fov_width_arcmin, preview.fov_height_arcmin) / 2.0 * 1.03


def text_anchor(screen_dx: float, screen_dy: float) -> tuple[str, str]:
    """matplotlib-style (ha, va) for a label placed past the end of a
    line pointing (screen_dx, screen_dy) — screen axes, y up — so the
    text extends away from the line instead of across it."""
    ha = "left" if screen_dx > 0.4 else "right" if screen_dx < -0.4 else "center"
    va = "bottom" if screen_dy > 0.4 else "top" if screen_dy < -0.4 else "center"
    return ha, va


def _import_matplotlib():
    """The lazy-import seam, factored out so tests can force the
    "matplotlib missing" path without needing to actually uninstall it."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, FancyArrowPatch, Polygon

    return plt, Circle, FancyArrowPatch, Polygon


def scale_bar_arcmin(view_half_arcmin: float) -> float:
    """The longest of `_SCALE_BAR_CHOICES_ARCMIN` within half the view's
    half-width."""
    fitting = [c for c in _SCALE_BAR_CHOICES_ARCMIN if c <= view_half_arcmin / 2.0]
    return fitting[-1] if fitting else _SCALE_BAR_CHOICES_ARCMIN[0]


def save_framing_preview(
    preview: FramingPreview,
    path: Path,
    *,
    title: str,
    caption_lines: Sequence[str],
    image: sky_survey.SurveyImage | None = None,
    local_tz: tzinfo | None = None,
) -> None:
    """Render `preview` as a PNG to `path`, overwriting whatever was
    there, with `image` as the backdrop if given. `local_tz` labels the
    zenith arrow and the orientation ring's hours (UTC if omitted). Raises
    `FrameExportUnavailable` if matplotlib isn't installed.
    """
    try:
        plt, Circle, FancyArrowPatch, Polygon = _import_matplotlib()
    except ImportError as exc:
        raise FrameExportUnavailable(
            "PNG export needs matplotlib, which isn't installed — run "
            "`uv sync --extra charts` and try again."
        ) from exc

    half = view_half_width_arcmin(preview, image)

    fig, ax = plt.subplots(figsize=(7, 7), facecolor=BACKGROUND_COLOR)
    ax.set_facecolor(BACKGROUND_COLOR)
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
            edgecolor=FRAME_COLOR,
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
                color=FRAME_COLOR,
                linewidth=1.5,
                zorder=3,
            )
        )
        ha, va = text_anchor(-up[0], up[1])
        when_text = preview.when.astimezone(local_tz or UTC)
        ax.annotate(
            f"zenith {when_text:%H:%M}",
            (end[0] + up[0] * length * 0.2, end[1] + up[1] * length * 0.2),
            color=FRAME_COLOR,
            fontsize=8,
            ha=ha,
            va=va,
            zorder=4,
        )

    ticks = orientation_ticks(preview, local_tz or UTC)
    if ticks:
        ring = orientation_ring_radius_arcmin(preview)
        ax.add_patch(
            Circle(
                (0.0, 0.0),
                ring,
                fill=False,
                edgecolor=CHROME_COLOR,
                linewidth=0.6,
                alpha=0.35,
                zorder=3,
            )
        )
        tick_length = half * 0.035
        for tick in ticks:
            angle_rad = math.radians(tick.angle_deg)
            up = (math.sin(angle_rad), math.cos(angle_rad))
            outer = ring + tick_length * (1.6 if tick.highlight else 1.0)
            ax.plot(
                [up[0] * ring, up[0] * outer],
                [up[1] * ring, up[1] * outer],
                color=FRAME_COLOR if tick.highlight else CHROME_COLOR,
                linewidth=2.2 if tick.highlight else 1.2,
                zorder=4,
            )
            if tick.label:
                ha, va = text_anchor(-up[0], up[1])
                label_r = outer + tick_length * 0.3
                ax.annotate(
                    tick.label,
                    (up[0] * label_r, up[1] * label_r),
                    color=CHROME_COLOR,
                    fontsize=7,
                    ha=ha,
                    va=va,
                    zorder=4,
                )

    below = labels_below(preview)
    for obj in preview.objects:
        color = PRIMARY_COLOR if obj.primary else NEIGHBOR_COLOR
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
        sign = -1.0 if below else 1.0
        ax.annotate(
            obj.target.catalog_id or obj.target.name,
            (center[0], center[1] + sign * label_offset),
            xytext=(0, sign * 4),
            textcoords="offset points",
            color=color,
            fontsize=9 if obj.primary else 7.5,
            fontweight="bold" if obj.primary else "normal",
            ha="center",
            va="top" if below else "bottom",
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
                color=CHROME_COLOR,
                linewidth=1.0,
                zorder=4,
            )
        )
        ax.annotate(
            label,
            (origin[0] + dx * 1.35, origin[1] + dy * 1.35),
            color=CHROME_COLOR,
            fontsize=8,
            ha="center",
            va="center",
            zorder=4,
        )

    # Scale bar (lower right).
    bar = scale_bar_arcmin(half)
    bar_right = -half * 0.85
    bar_y = -half * 0.9
    ax.plot(
        [bar_right + bar, bar_right],
        [bar_y, bar_y],
        color=CHROME_COLOR,
        linewidth=2.0,
        zorder=4,
    )
    ax.annotate(
        format_angle_arcmin(bar),
        (bar_right + bar / 2.0, bar_y),
        xytext=(0, 4),
        textcoords="offset points",
        color=CHROME_COLOR,
        fontsize=8,
        ha="center",
        va="bottom",
        zorder=4,
    )

    fig.text(
        0.02,
        0.985,
        title,
        color=PRIMARY_COLOR,
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
    footer.append(CIRCLE_NOTE)
    fig.text(
        0.02,
        0.01,
        "\n".join(footer),
        color=CHROME_COLOR,
        fontsize=8,
        ha="left",
        va="bottom",
        linespacing=1.5,
    )
    fig.subplots_adjust(
        left=0.02, right=0.98, top=0.94, bottom=0.02 + 0.026 * len(footer)
    )
    fig.savefig(path, dpi=150, facecolor=BACKGROUND_COLOR)
    plt.close(fig)

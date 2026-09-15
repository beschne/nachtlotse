"""PNG export of the shortlist-overview polar chart, for `lotse plan --chart`.

matplotlib is an optional extra (`uv sync --extra charts`), not a core
CLI dependency — this module only imports it lazily, inside
`save_shortlist_chart`, so `cli.py` itself never requires it just to
run `lotse plan` without `--chart`.
"""

from __future__ import annotations

from pathlib import Path

from nachtlotse import charting
from nachtlotse.planning import NightPlan

DEFAULT_CHART_FILENAME = "nachtlotse-shortlist.png"


class ChartExportUnavailable(Exception):
    """The `charts` extra (matplotlib) isn't installed."""


def _import_matplotlib():
    """The lazy-import seam, factored out so tests can force the
    "matplotlib missing" path without needing to actually uninstall it."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon

    return plt, Polygon


def save_shortlist_chart(plan: NightPlan, path: Path) -> None:
    """Render the shortlist's alt/az tracks as a polar PNG to `path`,
    overwriting whatever was already there.

    Raises `ChartExportUnavailable` if matplotlib isn't installed, or
    `ValueError` if there's nothing to chart (an empty shortlist).
    """
    if not plan.shortlist:
        raise ValueError("Nothing to chart: the shortlist is empty.")

    try:
        plt, Polygon = _import_matplotlib()
    except ImportError as exc:
        raise ChartExportUnavailable(
            "PNG export needs matplotlib, which isn't installed — run "
            "`uv sync --extra charts` and try again."
        ) from exc

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"aspect": "equal"})
    ax.set_xlim(-100, 100)
    ax.set_ylim(-100, 100)
    ax.axis("off")

    wedge_points = charting.horizon_wedge(plan.site)
    ax.add_patch(
        Polygon(
            wedge_points,
            closed=True,
            facecolor=charting.HORIZON_FILL_COLOR,
            edgecolor="none",
            alpha=0.5,
            zorder=1,
        )
    )

    for alt_deg in charting.GRID_RINGS_ALT_DEG:
        xs, ys = zip(*charting.grid_ring(alt_deg))
        ax.plot(xs, ys, color=charting.GRID_COLOR, linewidth=0.75, zorder=2)
        if alt_deg == 0.0:
            # The 0° ring sits right on the rim, at the same spot as the
            # "N" compass label — skip labeling it; the rim itself already
            # reads as the horizon.
            continue
        label_x, label_y = charting.project(alt_deg, az_deg=0.0)
        ax.annotate(
            f"{alt_deg:.0f}°",
            (label_x, label_y),
            fontsize=7,
            color=charting.LABEL_COLOR,
            ha="center",
            va="bottom",
            zorder=4,
        )

    for label, az_deg in charting.COMPASS_LABELS:
        x, y = charting.compass_label_point(az_deg, rim_r=98.0)
        ax.annotate(
            label, (x, y), fontsize=10, ha="center", va="center", zorder=4, fontweight="bold"
        )

    for i, track in enumerate(charting.shortlist_tracks(plan)):
        color = charting.SHORTLIST_PALETTE[i % len(charting.SHORTLIST_PALETTE)]
        for segment_index, segment in enumerate(track.segments):
            if len(segment) < 2:
                continue
            xs, ys = zip(*segment)
            ax.plot(
                xs,
                ys,
                color=color,
                linewidth=2.0,
                zorder=3,
                label=track.name if segment_index == 0 else None,
            )

    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=8, frameon=False)
    ax.set_title(f"{plan.site.name} — shortlist tonight", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)

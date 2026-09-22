"""The "Sites" and "Rigs" reference screens — what `lotse sites`/
`lotse rigs` print, as their own tabs.

Read-only, deliberately: `store.SITES`/`store.RIGS` come from
`sites_local.yaml`/`rigs_local.yaml`, hand-authored YAML files with
their own comments and formatting (see `store.py`) — round-tripping an
in-app editor through those without mangling them is real, separate
scope, not part of this first scaffold. These screens only surface
what's already configured, same as the CLI's own `sites`/`rigs`
commands.

`store.SITES`/`store.RIGS` themselves are loaded once at import time
and don't change while the app runs, so unlike the other tabs neither
is rebuilt on Re-plan. The Sites tab has two independent controls on
top of that fixed set, neither touching the underlying file: SORT
(`file order` — `sites_local.yaml`'s own order, the default; `region`;
`distance` from a chosen reference site, same haversine math the Best
Sky tab's own Distance column uses) picks the display order, and a
REGIONS checkbox row *filters* which sites show at all — orthogonal to
SORT, not nested under "region" (own checkboxes, one per distinct
region, all checked by default; see `data_adapter.sort_sites`'s
`regions` argument). Useful together for a large/growing site list:
narrow to one region, then order those by distance from a candidate
new site, say.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from nachtlotse.data.store import RigRecord, SiteRecord
from nachtlotse.gui import data_adapter
from nachtlotse.gui import export as gui_export
from nachtlotse.gui.theme import (
    COLORS,
    RoundedCard,
    field_label,
    label_style,
    secondary_button,
)

_SORT_LABELS: dict[data_adapter.SiteSortMode, str] = {
    "file": "File order",
    "region": "Region",
    "distance": "Distance",
}
_SORT_MODES: list[data_adapter.SiteSortMode] = list(_SORT_LABELS)


def _heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(
        label_style(
            f"color: {COLORS['ink_secondary']}; font-size: 12px; font-weight: 600; "
            "letter-spacing: 1px; margin-bottom: 4px;"
        )
    )
    return label


def _detail_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(
        label_style(f"color: {COLORS['ink_secondary']}; font-size: 12px;")
    )
    return label


def _name_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(
        label_style(f"color: {COLORS['ink']}; font-size: 14px; font-weight: 600;")
    )
    return label


def _site_card(record: SiteRecord, distance_text: str | None = None) -> QWidget:
    info = data_adapter.build_site_info(record)
    card = RoundedCard()
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(3)

    title = info.name + (f"  (aka {info.aliases_text})" if info.aliases_text else "")
    layout.addWidget(_name_label(title))
    layout.addWidget(_detail_label(info.coords_text))
    layout.addWidget(_detail_label(f"{info.region_text} · {info.horizon_text}"))
    if info.address:
        layout.addWidget(_detail_label(info.address))
    # Only set when the Sites tab's SORT is "Distance" (see
    # data_adapter.sort_sites) — "0 km" for the reference site itself.
    if distance_text is not None:
        layout.addWidget(_detail_label(distance_text))
    return card


def _rig_card(record: RigRecord) -> QWidget:
    info = data_adapter.build_rig_info(record)
    card = RoundedCard()
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(3)

    title = info.name + (f"  (aka {info.aliases_text})" if info.aliases_text else "")
    layout.addWidget(_name_label(title))
    layout.addWidget(_detail_label(info.optics_text))
    layout.addWidget(_detail_label(info.sensor_text))
    layout.addWidget(_detail_label(info.fov_text))
    layout.addWidget(_detail_label(info.limiting_mag_text))
    return card


def _list_content(
    heading_text: str, cards: list[QWidget], export_button: QWidget
) -> QWidget:
    """A single scrollable column's content: a heading + Export button row,
    then one card per record. The button sits in the heading row (not
    scrolled away with the cards) since it acts on the whole list, not
    any one record."""
    content = QWidget()
    content.setStyleSheet(f"background: {COLORS['cream']};")
    column = QVBoxLayout(content)
    column.setContentsMargins(4, 4, 4, 4)
    column.setSpacing(10)

    heading_row = QHBoxLayout()
    heading_row.addWidget(_heading(heading_text))
    heading_row.addStretch(1)
    heading_row.addWidget(export_button)
    column.addLayout(heading_row)

    for card in cards:
        column.addWidget(card)
    column.addStretch(1)
    return content


class _ListScrollArea(QScrollArea):
    def __init__(self, content: QWidget) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.setStyleSheet(
            f"QScrollArea {{ background: {COLORS['cream']}; border: none; }}"
        )
        self.setWidget(content)

    def _export(self, text: str, default_filename: str, dialog_title: str) -> None:
        default_path = str(gui_export.default_export_dir() / default_filename)
        path_str, _ = QFileDialog.getSaveFileName(
            self, dialog_title, default_path, "Text files (*.txt)"
        )
        if not path_str:
            return
        try:
            gui_export.write_text(text, Path(path_str))
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))


class SitesCard(_ListScrollArea):
    """Every configured site whose region is checked (REGIONS), one
    card each, in the order SORT picks (see module docstring) —
    `sites` itself (and its file order) never changes; only which of
    them show, and in what order, does."""

    def __init__(self, sites: list[SiteRecord]) -> None:
        self._sites = sites
        self._region_checkboxes: dict[str, QCheckBox] = {}

        export_button = secondary_button("Export .txt…")
        export_button.setEnabled(bool(sites))

        content = QWidget()
        content.setStyleSheet(f"background: {COLORS['cream']};")
        outer = QVBoxLayout(content)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(10)

        self._heading_label = _heading(f"SITES ({len(sites)})")
        heading_row = QHBoxLayout()
        heading_row.addWidget(self._heading_label)
        heading_row.addStretch(1)
        heading_row.addWidget(export_button)
        outer.addLayout(heading_row)

        if sites:
            outer.addLayout(self._build_sort_row())
            region_row = self._build_region_filter_row()
            if region_row is not None:
                outer.addLayout(region_row)

        self._empty_label = _detail_label("No sites match the checked regions.")
        self._empty_label.hide()
        outer.addWidget(self._empty_label)

        cards_container = QWidget()
        self._cards_column = QVBoxLayout(cards_container)
        self._cards_column.setContentsMargins(0, 0, 0, 0)
        self._cards_column.setSpacing(10)
        outer.addWidget(cards_container)

        super().__init__(content)

        export_button.clicked.connect(
            lambda: self._export(
                gui_export.sites_text(sites),
                gui_export.DEFAULT_SITES_TXT_FILENAME,
                "Export Sites",
            )
        )

        self._render()

    def _build_sort_row(self) -> QHBoxLayout:
        controls_style = f"""
            QComboBox {{
                background: {COLORS['cream']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 12px;
                color: {COLORS['ink']};
            }}
        """
        row = QHBoxLayout()
        row.addWidget(field_label("SORT"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([_SORT_LABELS[mode] for mode in _SORT_MODES])
        self.sort_combo.setStyleSheet(controls_style)
        self.sort_combo.currentIndexChanged.connect(self._render)
        row.addWidget(self.sort_combo)

        # Only meaningful (and only shown) for "Distance" — toggled by
        # _render() below, not fixed here, since the combo box a user
        # picks it from doesn't exist until this row is built.
        self._from_label = field_label("FROM")
        row.addWidget(self._from_label)
        self.from_combo = QComboBox()
        for record in self._sites:
            self.from_combo.addItem(record.site.name)
        self.from_combo.setStyleSheet(controls_style)
        self.from_combo.currentIndexChanged.connect(self._render)
        row.addWidget(self.from_combo)

        row.addStretch(1)
        return row

    def _build_region_filter_row(self) -> QHBoxLayout | None:
        """A checkbox per distinct region, all checked by default — a
        filter independent of SORT (not nested under `mode="region"`),
        so it's built and shown whenever there's more than one region
        to choose among, regardless of the current sort. None when
        every configured site shares one region: nothing to filter."""
        regions = sorted({record.region for record in self._sites}, key=str.casefold)
        if len(regions) < 2:
            return None

        row = QHBoxLayout()
        row.addWidget(field_label("REGIONS"))
        checkbox_style = f"QCheckBox {{ color: {COLORS['ink']}; font-size: 12px; }}"
        for region in regions:
            checkbox = QCheckBox(region)
            checkbox.setChecked(True)
            checkbox.setStyleSheet(checkbox_style)
            checkbox.toggled.connect(self._render)
            self._region_checkboxes[region] = checkbox
            row.addWidget(checkbox)
        row.addStretch(1)
        return row

    def _current_sort_mode(self) -> data_adapter.SiteSortMode:
        return _SORT_MODES[self.sort_combo.currentIndex()]

    def _selected_regions(self) -> set[str]:
        if not self._region_checkboxes:
            return {record.region for record in self._sites}
        return {
            region
            for region, checkbox in self._region_checkboxes.items()
            if checkbox.isChecked()
        }

    def _render(self) -> None:
        while self._cards_column.count():
            item = self._cards_column.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # hide() immediately, rather than leaving it to whenever
                # deleteLater()'s deferred deletion actually runs — taking
                # it out of the layout alone doesn't stop it painting, so
                # without this the old cards briefly show through behind
                # the newly re-sorted ones.
                widget.hide()
                widget.deleteLater()

        if not self._sites:
            return

        mode = self._current_sort_mode()
        is_distance = mode == "distance"
        self._from_label.setVisible(is_distance)
        self.from_combo.setVisible(is_distance)
        reference = self._sites[self.from_combo.currentIndex()] if is_distance else None

        selected_regions = self._selected_regions()
        rows = data_adapter.sort_sites(
            self._sites, mode, reference, regions=selected_regions
        )

        self._heading_label.setText(
            f"SITES ({len(rows)})"
            if len(rows) == len(self._sites)
            else f"SITES ({len(rows)} of {len(self._sites)})"
        )
        self._empty_label.setVisible(not rows)

        for row in rows:
            self._cards_column.addWidget(_site_card(row.site_record, row.distance_text))
        self._cards_column.addStretch(1)


class RigsCard(_ListScrollArea):
    """Every configured rig, one card each — built once from `store.RIGS`."""

    def __init__(self, rigs: list[RigRecord]) -> None:
        export_button = secondary_button("Export .txt…")
        export_button.setEnabled(bool(rigs))
        super().__init__(
            _list_content(
                f"RIGS ({len(rigs)})", [_rig_card(r) for r in rigs], export_button
            )
        )
        export_button.clicked.connect(
            lambda: self._export(
                gui_export.rigs_text(rigs),
                gui_export.DEFAULT_RIGS_TXT_FILENAME,
                "Export Rigs",
            )
        )

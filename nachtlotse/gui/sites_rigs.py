"""The "Sites" and "Rigs" reference screens — what `lotse sites`/
`lotse rigs` print, as their own tabs.

Read-only, deliberately: `store.SITES`/`store.RIGS` come from
`sites_local.yaml`/`rigs_local.yaml`, hand-authored YAML files with
their own comments and formatting (see `store.py`) — round-tripping an
in-app editor through those without mangling them is real, separate
scope, not part of this first scaffold. These screens only surface
what's already configured, same as the CLI's own `sites`/`rigs`
commands.

Static once built: `store.SITES`/`store.RIGS` are loaded once at import
time and don't change while the app runs, so unlike the other tabs
these aren't rebuilt on Re-plan.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
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
from nachtlotse.gui.theme import COLORS, RoundedCard, label_style, secondary_button


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


def _site_card(record: SiteRecord) -> QWidget:
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
    """Every configured site, one card each — built once from `store.SITES`."""

    def __init__(self, sites: list[SiteRecord]) -> None:
        export_button = secondary_button("Export .txt…")
        export_button.setEnabled(bool(sites))
        super().__init__(
            _list_content(
                f"SITES ({len(sites)})", [_site_card(r) for r in sites], export_button
            )
        )
        export_button.clicked.connect(
            lambda: self._export(
                gui_export.sites_text(sites),
                gui_export.DEFAULT_SITES_TXT_FILENAME,
                "Export Sites",
            )
        )


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

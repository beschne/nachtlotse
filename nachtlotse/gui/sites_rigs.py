"""The "Sites & Rigs" reference screen — what `lotse sites`/`lotse rigs`
print, shown side by side instead.

Read-only, deliberately: `store.SITES`/`store.RIGS` come from
`sites_local.yaml`/`rigs_local.yaml`, hand-authored YAML files with
their own comments and formatting (see `store.py`) — round-tripping an
in-app editor through those without mangling them is real, separate
scope, not part of this first scaffold. This screen only surfaces what's
already configured, same as the CLI's own `sites`/`rigs` commands.

Static once built: `store.SITES`/`store.RIGS` are loaded once at import
time and don't change while the app runs, so unlike the other tabs this
one isn't rebuilt on Re-plan.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from nachtlotse.data.store import RigRecord, SiteRecord
from nachtlotse.gui import data_adapter
from nachtlotse.gui.theme import COLORS, RoundedCard, label_style


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
    label.setStyleSheet(label_style(f"color: {COLORS['ink_secondary']}; font-size: 12px;"))
    return label


def _name_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(label_style(f"color: {COLORS['ink']}; font-size: 14px; font-weight: 600;"))
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


class SitesRigsCard(QScrollArea):
    """Two scrollable columns: every configured site, every configured
    rig — built once from `store.SITES`/`store.RIGS`."""

    def __init__(self, sites: list[SiteRecord], rigs: list[RigRecord]) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.setStyleSheet(f"QScrollArea {{ background: {COLORS['cream']}; border: none; }}")

        content = QWidget()
        content.setStyleSheet(f"background: {COLORS['cream']};")
        columns = QHBoxLayout(content)
        columns.setContentsMargins(4, 4, 4, 4)
        columns.setSpacing(20)

        sites_column = QVBoxLayout()
        sites_column.setSpacing(10)
        sites_column.addWidget(_heading(f"SITES ({len(sites)})"))
        for record in sites:
            sites_column.addWidget(_site_card(record))
        sites_column.addStretch(1)
        columns.addLayout(sites_column, stretch=1)

        rigs_column = QVBoxLayout()
        rigs_column.setSpacing(10)
        rigs_column.addWidget(_heading(f"RIGS ({len(rigs)})"))
        for record in rigs:
            rigs_column.addWidget(_rig_card(record))
        rigs_column.addStretch(1)
        columns.addLayout(rigs_column, stretch=1)

        self.setWidget(content)

"""Design tokens + shared widgets for the native GUI.

Colors are the Claude Design system's own tokens (`tokens/colors.css` in
the "Nachtlotse design system" project), not re-approximated — the same
values the design kit's screens use. Only light mode is wired up for now;
`DARK_COLORS` is captured for when a theme toggle gets built (see
ROADMAP.md/STATUS.md for what's still missing from this first scaffold).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QLabel

LIGHT_COLORS = {
    "cream": "#f6f2ea",
    "cream_hover": "#fbf9f4",
    "paper": "#fffdf8",
    "border": "#e5ddcd",
    "border_strong": "#d8cdb8",
    "ink": "#2a2621",
    "ink_secondary": "#726b5d",
    "ink_muted": "#8c8474",
    "text_on_accent": "#fffaf5",
    "clay": "#c96442",
    "clay_hover": "#b8552f",
    "clay_press": "#a54a28",
    "clay_tint": "#f4e2d8",
    "go": "#56744a",
    "go_text": "#435b38",
    "go_tint": "#e7eedf",
    "marginal": "#b07d2b",
    "marginal_text": "#7d5715",
    "marginal_tint": "#f4e8ce",
    "skip": "#9c5044",
    "skip_text": "#813a30",
    "skip_tint": "#f0dcd6",
}

DARK_COLORS = {
    "cream": "#1a1712",
    "cream_hover": "#201d18",
    "paper": "#262219",
    "border": "#34302a",
    "border_strong": "#423d35",
    "ink": "#ece6da",
    "ink_secondary": "#a49b89",
    "ink_muted": "#857c6c",
    "text_on_accent": "#241109",
    "clay": "#e0805e",
    "clay_hover": "#eb9271",
    "clay_press": "#f2a486",
    "clay_tint": "#3a2a22",
    "go": "#7fb36a",
    "go_text": "#a9c79a",
    "go_tint": "#24301f",
    "marginal": "#d7a94f",
    "marginal_text": "#e6c886",
    "marginal_tint": "#332a17",
    "skip": "#cc8578",
    "skip_text": "#e0a99d",
    "skip_tint": "#33211d",
}

# The dark polar sky chart stays dark regardless of app theme — a night
# sky doesn't get a light-mode variant. Values from tokens/colors.css.
SKY_COLORS = {
    "canvas": "#0b1120",
    "rim": "#1b2740",
    "grid": "rgba(150,168,208,0.16)",
    "grid_strong": "rgba(150,168,208,0.32)",
    "label": "#8ea0c6",
    "star": "#f3efe4",
    "go": "#7fb36a",
    "marginal": "#e2b45c",
    "skip": "#cc8578",
    "moon": "#ddcf94",
}

# Only light mode is wired up in this first scaffold — swap this binding
# once a theme toggle exists.
COLORS = LIGHT_COLORS

VERDICT_COLORS = {
    "GO": (COLORS["go_text"], COLORS["go_tint"]),
    "MARGINAL": (COLORS["marginal_text"], COLORS["marginal_tint"]),
    "SKIP": (COLORS["skip_text"], COLORS["skip_tint"]),
}


def label_style(rules: str) -> str:
    """Every plain-text QLabel needs an explicit transparent background.

    Undocumented-until-you-hit-it Qt behavior: once *any* stylesheet is
    set anywhere in the app, QLabel (itself a QFrame subclass) starts
    painting an opaque default-palette background instead of staying
    see-through, even for labels with no matching selector of their own.
    Found the hard way in the PySide6-vs-PyObjC framework spike (see
    ROADMAP.md's native macOS app entry). `VerdictBadge` below is
    unaffected: it *wants* an opaque tinted background.
    """
    return f"background: transparent; border: none; {rules}"


class RoundedCard(QFrame):
    """A soft-shadowed, rounded-corner container — the design system's
    signature "content floats on cream" look.

    The stylesheet is scoped to `#roundedCard` (this instance's object
    name), not the bare `QFrame` type selector — QLabel (and other
    widgets) are themselves QFrame subclasses in Qt, so a bare
    `QFrame { border: ...; background: ... }` rule cascades to every
    child label inside the card too. Also found the hard way in the spike.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("roundedCard")
        self.setStyleSheet(
            f"""
            QFrame#roundedCard {{
                background: {COLORS["paper"]};
                border-radius: 16px;
                border: 1px solid {COLORS["border"]};
            }}
            """
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 35))
        self.setGraphicsEffect(shadow)


class VerdictBadge(QLabel):
    """A colored, rounded pill for a GO/MARGINAL/SKIP verdict.

    `WA_StyledBackground` (belt-and-braces correctness for a stylesheet
    background/border-radius on a QWidget-derived class) and a fixed
    size taken from `sizeHint()` (so the badge never gets stretched by
    a parent layout). Neither turned out to be the fix for the "badge
    looked incompletely colored" bug reported during GUI testing — that
    was the plain `QWidget` wrapping this badge in a `QTableWidget` cell
    (`main_window._verdict_cell`) painting an opaque default-palette box
    around it; see that method's own comment.
    """

    def __init__(self, level: str) -> None:
        super().__init__(level)
        fg, bg = VERDICT_COLORS[level]
        self.setAlignment(Qt.AlignCenter)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            f"""
            QLabel {{
                color: {fg};
                background: {bg};
                border-radius: 9px;
                padding: 3px 10px;
                font-weight: 600;
                font-size: 11px;
            }}
            """
        )
        self.setFixedSize(self.sizeHint())

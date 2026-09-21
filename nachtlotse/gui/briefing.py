"""The LLM nightly-briefing screen — `prose.generate_nightly_briefing`
surfaced in the GUI.

Keeps the same rules `prose.py`'s own module docstring lays out: the
Anthropic API is never called until the user explicitly clicks
"Generate briefing" (mirrors the CLI's `--prose` flag — nothing fires on
its own the way `plan_night`'s weather fetch does), and any failure
(`prose.ProseUnavailable`: missing `anthropic` package, no API key,
request error) is shown as a visible error, never swallowed.

The request runs on a background `QThread` (`_BriefingWorker`) so the UI
doesn't freeze for the seconds a real API round-trip takes.
`nachtlotse.prose` itself is safe to import unconditionally here — it
only lazily imports `anthropic` inside the request path (see
`prose._import_anthropic`), so this module needs no lazy-import dance
of its own, just like `cli.py` doesn't.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout

from nachtlotse import prose
from nachtlotse.gui.theme import COLORS, RoundedCard, label_style
from nachtlotse.planning import NightPlan, NightPlanForBestRig

_PLACEHOLDER = (
    'Click "Generate briefing" to have Claude phrase tonight\'s plan as a '
    "short prose summary. Nothing is sent to Anthropic until you ask."
)


class _BriefingWorker(QThread):
    """Runs `prose.generate_nightly_briefing` off the UI thread."""

    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, plan: NightPlan | NightPlanForBestRig) -> None:
        super().__init__()
        self._plan = plan

    def run(self) -> None:
        try:
            text = prose.generate_nightly_briefing(self._plan)
        except prose.ProseUnavailable as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(text)


def _output_style(*, error: bool) -> str:
    bg = COLORS["skip_tint"] if error else COLORS["paper"]
    fg = COLORS["skip_text"] if error else COLORS["ink"]
    border = COLORS["skip"] if error else COLORS["border"]
    return f"""
        QTextEdit {{
            background: {bg}; color: {fg};
            border: 1px solid {border}; border-radius: 10px;
            padding: 12px; font-size: 13px;
        }}
    """


class BriefingCard(RoundedCard):
    """A Generate button plus the resulting prose (or a loud error)."""

    def __init__(self) -> None:
        super().__init__()
        self._plan: NightPlan | NightPlanForBestRig | None = None
        self._worker: _BriefingWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QLabel("Nightly briefing")
        header.setStyleSheet(
            label_style(f"color: {COLORS['ink']}; font-size: 16px; font-weight: 600;")
        )
        layout.addWidget(header)

        self.generate_button = QPushButton("Generate briefing")
        self.generate_button.setStyleSheet(
            f"""
            QPushButton {{
                background: {COLORS['clay']}; color: {COLORS['text_on_accent']};
                border: none; border-radius: 8px; padding: 8px 16px;
                font-size: 13px; font-weight: 600;
            }}
            QPushButton:hover {{ background: {COLORS['clay_hover']}; }}
            QPushButton:pressed {{ background: {COLORS['clay_press']}; }}
            QPushButton:disabled {{
                background: {COLORS['border_strong']}; color: {COLORS['ink_muted']};
            }}
            """
        )
        self.generate_button.clicked.connect(self._on_generate_clicked)
        button_row = QHBoxLayout()
        button_row.addWidget(self.generate_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet(_output_style(error=False))
        self.output.setPlaceholderText(_PLACEHOLDER)
        layout.addWidget(self.output, stretch=1)

    def set_plan(self, plan: NightPlan | NightPlanForBestRig) -> None:
        """A new plan invalidates any prior briefing — it described the
        old plan's facts, not this one's, so clear rather than keep it
        showing under new site/rig/date controls."""
        self._plan = plan
        self.output.setStyleSheet(_output_style(error=False))
        self.output.clear()
        self.output.setPlaceholderText(_PLACEHOLDER)
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Generate briefing")

    def _on_generate_clicked(self) -> None:
        if self._plan is None:
            return
        self.generate_button.setEnabled(False)
        self.generate_button.setText("Generating…")
        self.output.setStyleSheet(_output_style(error=False))
        self.output.setPlainText("")
        self._worker = _BriefingWorker(self._plan)
        self._worker.succeeded.connect(self._on_succeeded)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_succeeded(self, text: str) -> None:
        self.output.setStyleSheet(_output_style(error=False))
        self.output.setPlainText(text)
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Regenerate")

    def _on_failed(self, message: str) -> None:
        self.output.setStyleSheet(_output_style(error=True))
        self.output.setPlainText(message)
        self.generate_button.setEnabled(True)
        self.generate_button.setText("Generate briefing")

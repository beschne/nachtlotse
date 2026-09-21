"""`lotse gui`'s entry point.

Only ever imported lazily, from `cli.py`'s `gui` subcommand handler —
importing PySide6 at all is what the `gui` extra exists to make optional
(see this package's own docstring).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from nachtlotse.data import store
from nachtlotse.gui.main_window import MainWindow

_APP_ICON_PATH = Path(__file__).resolve().parent / "assets" / "app_icon.png"


def main() -> int:
    app = QApplication(sys.argv)
    # QApplication.setWindowIcon() also updates the Dock tile on macOS at
    # runtime (via NSApp), even though `lotse gui` isn't a bundled .app
    # with its own Info.plist/.icns — no packaging step needed for this.
    app.setWindowIcon(QIcon(str(_APP_ICON_PATH)))

    try:
        store.require_sites()
        store.require_rigs()
    except ValueError as exc:
        QMessageBox.critical(None, "Nachtlotse", str(exc))
        return 2

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

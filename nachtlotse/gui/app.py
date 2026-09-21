"""`lotse gui`'s entry point.

Only ever imported lazily, from `cli.py`'s `gui` subcommand handler —
importing PySide6 at all is what the `gui` extra exists to make optional
(see this package's own docstring).
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from nachtlotse.data import store
from nachtlotse.gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)

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

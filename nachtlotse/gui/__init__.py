"""The native macOS GUI (`lotse gui`) — PySide6, chosen over PyObjC/AppKit
after a hands-on framework spike (see ROADMAP.md's "Native macOS app").

Same dependency direction as `cli.py`: this package calls into
`planning`/`engine`/`data` and nothing calls back into it. `pyside6` is an
optional extra (`uv sync --extra gui`) the plain CLI never needs — `cli.py`
only imports this package lazily, inside the `gui` subcommand's handler.
"""

# Screenshots

`gui-shortlist.png` and `gui-sky-chart.png` are real screenshots of
`lotse gui` — the same site/rig/date plan, two tabs — embedded near the
top of the main [README.md](../README.md). No illustrative/fake data;
same rule the GUI itself follows.

`gui-best-sky.png` is the same real run's Best sky tab (Center defaulted
to the same site as the other two) — kept here for reference, not
currently embedded in README.md.

## Regenerating them

Whenever the GUI changes enough to make these look stale:

```bash
uv sync --extra gui
uv run --extra gui --with pyobjc-framework-Quartz \
    python3 screenshots/update_screenshots.py
```

This drives the real `MainWindow` in a single script — no clicking
around and hoping a simulated mouse click lands on the right tab; it
switches tabs via `QTabWidget.setCurrentIndex()` directly, since the
script already holds the window object it's capturing. It needs
`pyobjc-framework-Quartz` (to look up the window's `CGWindowID`) and the
system `screencapture`/`sips` tools (both ship with macOS) — none of
which the app itself needs, so it's a `--with` extra for this script
only, not part of the `gui` optional-dependency group.

To capture a different site/rig/date combination, edit `SITE_NAME`,
`RIG_NAME`, and `TARGET_DATE` at the top of `update_screenshots.py` —
whatever you pick must already exist in your own `sites_local.yaml`/
`rigs_local.yaml`. Update the caption text in README.md's screenshot
block to match; the script only overwrites the three PNGs, not that text.

Images are resized to 1600px wide (`sips -Z`) to keep the repo
reasonable — full native screen resolution isn't needed for a README.

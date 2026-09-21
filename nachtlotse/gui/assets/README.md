# App icon

`app_icon.png` (loaded by `gui/app.py` via `QIcon` for the Dock/window
icon at runtime) and `app_icon.icns` (a real multi-resolution icns, for
whenever this project gets packaged as a proper `.app` bundle) are both
generated, not hand-drawn in an image editor.

## Regenerating

Whenever the design should change:

```bash
uv run --with pillow python3 nachtlotse/gui/assets/generate_icon.py
```

This redraws both files from scratch — a crescent moon and accent star
on the app's own `ink` tone, using the exact hex values from
`gui/theme.py` rather than re-picked colors — and rebuilds the `.icns`
with macOS's own `sips`/`iconutil` (same tools Xcode uses), so it needs
macOS. No image-editing software involved.

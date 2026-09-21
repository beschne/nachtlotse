"""Regenerates the Nachtlotse app icon (Dock + menu bar).

Draws a crescent moon + accent star on the app's own dark `ink` tone,
using the exact hex values from `gui/theme.py` (not re-eyeballed) — a
crescent, since the app is itself about reading the night sky, and a
palette lifted straight from the design tokens rather than invented for
this one asset. Drawn at 4x and downsampled for clean edges (no
anti-aliased vector renderer needed for shapes this simple).

Produces two files this package ships:
  - `app_icon.png`  — 1024x1024, what `gui/app.py` loads at runtime via
    `QIcon` (Qt scales it down for the Dock/window icon; no bundled .app
    means there's no Info.plist to point at a .icns for the OS itself).
  - `app_icon.icns` — a real multi-resolution icns, built with the same
    macOS tools Xcode itself uses (`iconutil`), kept alongside for
    whenever this project gets packaged as a proper .app bundle
    (py2app/PyInstaller) — those tools want an .icns, not a PNG.

Needs Pillow (not a runtime dependency of the app itself, so run this
with `--with pillow`) and macOS's own `sips`/`iconutil` (always present).
Run with:

    uv run --with pillow python3 nachtlotse/gui/assets/generate_icon.py
"""

from __future__ import annotations

import math
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

# Straight from gui/theme.py's LIGHT_COLORS — not re-picked for this icon.
_INK = "#2a2621"
_PAPER = "#fffdf8"
_CLAY = "#c96442"

_ASSETS_DIR = Path(__file__).resolve().parent
_SCALE = 4
_SIZE = 1024 * _SCALE

# (filename, pixel size) pairs `iconutil` requires inside a .iconset.
_ICONSET_SIZES = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]


def _star(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill: str) -> None:
    """An 8-point sparkle: alternating long/short spokes from the center."""
    points = []
    for i in range(8):
        angle = math.pi / 4 * i
        radius = r if i % 2 == 0 else r * 0.38
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    draw.polygon(points, fill=fill)


def _render_1024() -> Image.Image:
    img = Image.new("RGBA", (_SIZE, _SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = int(0.04 * _SIZE)
    radius = int(0.225 * _SIZE)
    draw.rounded_rectangle([margin, margin, _SIZE - margin, _SIZE - margin], radius=radius, fill=_INK)

    # Crescent: a paper-colored disk with an offset disk of the same
    # background cut out of it, via alpha subtraction — simpler and
    # crisper than trying to path a crescent outline directly.
    moon_r = _SIZE * 0.235
    moon_cx, moon_cy = _SIZE * 0.44, _SIZE * 0.46
    cut_r = moon_r * 1.02
    cut_cx = moon_cx + moon_r * 0.62
    cut_cy = moon_cy - moon_r * 0.28

    moon_layer = Image.new("RGBA", (_SIZE, _SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(moon_layer).ellipse(
        [moon_cx - moon_r, moon_cy - moon_r, moon_cx + moon_r, moon_cy + moon_r], fill=_PAPER
    )
    cut_layer = Image.new("RGBA", (_SIZE, _SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(cut_layer).ellipse(
        [cut_cx - cut_r, cut_cy - cut_r, cut_cx + cut_r, cut_cy + cut_r], fill=(255, 255, 255, 255)
    )
    moon_layer.putalpha(ImageChops.subtract(moon_layer.split()[3], cut_layer.split()[3]))
    img = Image.alpha_composite(img, moon_layer)
    draw = ImageDraw.Draw(img)

    _star(draw, _SIZE * 0.70, _SIZE * 0.685, _SIZE * 0.105, _CLAY)
    _star(draw, _SIZE * 0.755, _SIZE * 0.325, _SIZE * 0.028, _PAPER)
    _star(draw, _SIZE * 0.30, _SIZE * 0.78, _SIZE * 0.022, _PAPER)

    return img.resize((1024, 1024), Image.LANCZOS)


def main() -> int:
    icon_1024 = _render_1024()
    png_path = _ASSETS_DIR / "app_icon.png"
    icon_1024.save(png_path)

    with tempfile.TemporaryDirectory() as tmp:
        iconset_dir = Path(tmp) / "app_icon.iconset"
        iconset_dir.mkdir()
        for filename, size in _ICONSET_SIZES:
            subprocess.run(
                ["sips", "-z", str(size), str(size), str(png_path), "--out", str(iconset_dir / filename)],
                check=True,
                capture_output=True,
            )
        icns_path = _ASSETS_DIR / "app_icon.icns"
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)], check=True
        )

    print(f"Wrote {png_path.name} and {icns_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

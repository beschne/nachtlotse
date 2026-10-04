"""Publish docs/wiki/ to the GitHub wiki.

The wiki is a separate git repository (<repo>.wiki.git). The pages live in
this repository under docs/wiki/ (English in en/, German in de/, plus Home,
Startseite, _Sidebar and _Footer); this script copies them into a fresh
clone of the wiki, flattened into one folder (GitHub shows wiki pages flat
anyway, and relative image links only resolve from the top level), adds the
screenshots from screenshots/ as images/, and commits.

    uv run python scripts/publish_wiki.py          # show what would change
    uv run python scripts/publish_wiki.py --push   # commit and push

Without --push nothing leaves this machine. Anything edited directly in the
GitHub wiki is replaced, since docs/wiki/ is the source.

The wiki repository only exists after its first page was saved once in
the GitHub web interface (Wiki tab -> "Create the first page").
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIKI_SOURCE = ROOT / "docs" / "wiki"
SCREENSHOTS = ROOT / "screenshots"


def run(*args: str, cwd: Path = ROOT, capture: bool = False) -> str:
    result = subprocess.run(
        args, cwd=cwd, check=True, text=True, capture_output=capture
    )
    return result.stdout.strip() if capture else ""


def wiki_remote() -> str:
    origin = run("git", "remote", "get-url", "origin", capture=True)
    return origin.removesuffix(".git") + ".wiki.git"


def collect_pages() -> dict[str, Path]:
    """Every page by its published file name; names must be unique,
    because the wiki is flat."""
    pages: dict[str, Path] = {}
    for path in sorted(WIKI_SOURCE.rglob("*.md")):
        if path.name in pages:
            sys.exit(f"Duplicate page name {path.name}: {pages[path.name]} and {path}")
        pages[path.name] = path
    return pages


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--push", action="store_true", help="commit and push")
    args = parser.parse_args()

    dirty = run(
        "git", "status", "--porcelain", "--", "docs/wiki", "screenshots", capture=True
    )
    if dirty:
        print("Note: docs/wiki/ or screenshots/ have uncommitted changes:")
        print(dirty)
    source_commit = run("git", "rev-parse", "--short", "HEAD", capture=True)

    pages = collect_pages()
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "wiki"
        try:
            run("git", "clone", "--quiet", wiki_remote(), str(clone))
        except subprocess.CalledProcessError:
            print(
                "Could not clone the wiki. Save its first page once on GitHub "
                "(Wiki tab -> Create the first page), then run this again.",
                file=sys.stderr,
            )
            return 2

        for item in clone.iterdir():
            if item.name == ".git":
                continue
            shutil.rmtree(item) if item.is_dir() else item.unlink()
        for name, path in pages.items():
            shutil.copy2(path, clone / name)
        images = clone / "images"
        images.mkdir()
        for png in sorted(SCREENSHOTS.glob("*.png")):
            shutil.copy2(png, images / png.name)

        run("git", "add", "--all", cwd=clone)
        changes = run("git", "status", "--short", cwd=clone, capture=True)
        if not changes:
            print("The wiki is already up to date.")
            return 0
        print(f"{len(pages)} pages, changes against the published wiki:")
        print(changes)
        if not args.push:
            print("\nDry run. Add --push to commit and publish.")
            return 0

        run(
            "git",
            "commit",
            "--quiet",
            "-m",
            f"Publish docs/wiki from {source_commit}",
            cwd=clone,
        )
        run("git", "push", "--quiet", cwd=clone)
        print("Published.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

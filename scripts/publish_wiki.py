"""Publish docs/wiki/ to the GitHub wiki.

The wiki is a separate git repository (<repo>.wiki.git). The pages live in
this repository under docs/wiki/ (English in en/, German in de/, plus Home,
Startseite, and a _Sidebar/_Footer per language); this script copies them
into a fresh clone of the wiki, adds the screenshots from screenshots/ as
images/, and commits.

Layout in the wiki: English pages and Home at the top level, German pages
in de/. GitHub shows every page at a flat address either way, but it takes
the _Sidebar.md and _Footer.md from the folder of the page being shown, so
German pages get the German sidebar and English pages the English one.
Pages link those images by absolute URL
(https://raw.githubusercontent.com/wiki/<owner>/<repo>/images/...): a
relative "images/x.png" resolves against the page address, and from
".../wiki/Startseite/" GitHub reads "images" as a page version ("Could not
find version images").

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
    """Every file by its path in the wiki: German pages (anything under
    docs/wiki/de/) in de/, everything else at the top level. Page names
    must be unique across both, because page addresses are flat;
    _Sidebar.md and _Footer.md exist once per language on purpose."""
    pages: dict[str, Path] = {}
    names: dict[str, Path] = {}
    for path in sorted(WIKI_SOURCE.rglob("*.md")):
        german = WIKI_SOURCE / "de" in path.parents
        target = f"de/{path.name}" if german else path.name
        if target in pages:
            sys.exit(f"Two files publish as {target}: {pages[target]} and {path}")
        if not path.name.startswith("_"):
            if path.name in names:
                sys.exit(
                    f"Duplicate page name {path.name}: {names[path.name]} and {path}"
                )
            names[path.name] = path
        pages[target] = path
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
        for target, path in pages.items():
            (clone / target).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, clone / target)
        images = clone / "images"
        images.mkdir()
        for png in sorted(SCREENSHOTS.glob("*.png")):
            shutil.copy2(png, images / png.name)

        run("git", "add", "--all", cwd=clone)
        changes = run("git", "status", "--short", cwd=clone, capture=True)
        if not changes:
            print("The wiki is already up to date.")
            return 0
        print(f"{len(pages)} files, changes against the published wiki:")
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

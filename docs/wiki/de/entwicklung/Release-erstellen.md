**English:** [Releasing](Releasing)

Ein Release läuft so ab:

1. Auf einem Branch arbeiten, ein Thema pro Branch, kleine Commits.
2. `uv run pytest` und `uv run ruff check .` ausführen.
3. Wenn sich in der App etwas sichtbar geändert hat, die Bildschirmfotos neu
   erzeugen:
   `uv run --extra gui --with pyobjc-framework-Quartz python3 screenshots/update_screenshots.py`.
4. Die Dokumentation nachziehen: `ROADMAP.md`, `STATUS.md`, bei Bedarf
   `README.md`, und die Wiki-Seiten in `docs/wiki/` (beide Sprachen).
5. Die Version in `pyproject.toml` erhöhen und `uv lock` ausführen.
6. In `main` zusammenführen, taggen (`git tag -a vX.Y.Z -m vX.Y.Z`), `main`
   und den Tag pushen.
7. Das GitHub-Release mit Notizen anlegen: `gh release create vX.Y.Z`.
8. Das Wiki veröffentlichen: `uv run python scripts/publish_wiki.py`.

## Das Wiki

Die Wiki-Seiten liegen in `docs/wiki/` im Repository, Englisch in `en/`,
Deutsch in `de/`, jede Sprache mit eigener Seitenleiste und Fußzeile.
`scripts/publish_wiki.py` kopiert sie zusammen mit den Bildschirmfotos ins
Wiki und pusht. Änderungen direkt im GitHub-Wiki werden
dabei überschrieben, bearbeite also immer die Dateien im Repository.

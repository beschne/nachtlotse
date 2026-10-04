**Deutsch:** [Release erstellen](Release-erstellen)

A release goes like this:

1. Work on a branch, one topic per branch, small commits.
2. Run `uv run pytest` and `uv run ruff check .`.
3. If anything in the app looks different, regenerate the screenshots:
   `uv run --extra gui --with pyobjc-framework-Quartz python3 screenshots/update_screenshots.py`.
4. Update the documentation: `ROADMAP.md`, `STATUS.md`, `README.md` if
   needed, and the wiki pages in `docs/wiki/` (both languages).
5. Raise the version in `pyproject.toml` and run `uv lock`.
6. Merge into `main`, tag it (`git tag -a vX.Y.Z -m vX.Y.Z`) and push
   `main` and the tag.
7. Create the GitHub release with notes: `gh release create vX.Y.Z`.
8. Publish the wiki: `uv run python scripts/publish_wiki.py`.

## The wiki

The wiki pages live in `docs/wiki/` in the repository, English in `en/`,
German in `de/`, each language with its own sidebar and footer.
`scripts/publish_wiki.py` copies them, together with the screenshots, into
the wiki and pushes. Edits made directly in the GitHub
wiki get overwritten, so always edit the files in the repository.

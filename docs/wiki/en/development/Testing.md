**Deutsch:** [Tests](Tests)

```bash
uv run pytest                                  # all tests
uv run --extra charts --extra gui pytest       # including PNG and app tests
uv run ruff check .                            # lint
uv run ruff format .                           # format
```

The suite has over 400 tests and runs in about 20 seconds.

Astronomy is tested against known values from independent sources, not
against the code's own formulas: transit altitudes, Polaris at the site's
latitude, the parallactic angle against the textbook formula, comet
positions against JPL Horizons, sky offsets against astropy.

The tests never go online. Every network source is replaced by a fake in
`tests/conftest.py`, and each test gets its own empty cache folder. Tests
that need matplotlib or PySide6 skip themselves when the extra isn't
installed. The app tests run without a window.

Every new rule in the engine comes with a test against a known value.

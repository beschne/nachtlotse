# Nachtlotse

*("Nachtlotse" is German for "night pilot" — like a harbor pilot who guides
ships through difficult waters, but for clear nights and telescopes.)*

> My pilot through clear nights. Answers the oldest question in astrophotography:
> **"What should I shoot tonight?"** — and delivers an honest verdict.

A deterministic session planner for astrophotography, native on macOS. It scores
tonight's sky over a given site against a given equipment rig and distills the
result down to **one** hero target plus a verdict: **GO / MARGINAL / SKIP** —
with a traceable rationale.

Modeled after [Clear Night Coach](https://clearnightcoach.com) (Windows-only).
Nachtlotse rebuilds the same core cross-platform — with an open, testable engine.

## Guiding principle

**The engine decides. An LLM formulates at most the prose — never the astronomy.**

Every altitude, every window, every framing number comes deterministically from
`skyfield`/`astroplan` against JPL ephemerides. The engine core
(`nachtlotse/engine/`) is pure Python with no UI, network, or I/O dependency, and
is fully backed by `pytest` against known astronomical values.

## Status

✅ **M0 — Scaffolding & engine core**, done.

- `nachtlotse/engine/models.py` — data model (`Site`, `HorizonProfile`, `Optics`,
  `Sensor`, `Mount`, `Rig`, `Target`, `Verdict`) as immutable dataclasses.
- `nachtlotse/engine/ephemeris.py` — altitude/azimuth/transit time of a target
  via `skyfield`.
- `nachtlotse/data/catalog.py` — Messier core catalog (30 objects).
- `nachtlotse/cli.py` — `lotse today`, ranking tonight's targets by max altitude
  for the hardcoded reference site (Bad Homburg) and rig (ZWO Seestar S30 Pro).
- Tests against independently known astronomical values (Polaris altitude ≈
  geographic latitude, transit altitude = 90° − lat + dec) plus catalog/CLI
  smoke tests.

Not yet implemented (by design, later milestones): twilight/dark-window,
moon-distance, and horizon constraints — `lotse today` currently ranks by raw
transit altitude only, day or night.

The full roadmap (M0–M6) and all architecture decisions are documented in
[`CLAUDE.md`](./CLAUDE.md).

## Quickstart

Requires [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync                # set up the environment + dependencies
uv run pytest          # run the tests
uv run ruff check .    # lint
uv run ruff format .   # format
uv run lotse today     # rank tonight's targets for Bad Homburg + Seestar S30 Pro
```

`uv run <cmd>` runs the command inside the project's own virtual environment
(`.venv`), managed by `uv` — no need to activate it manually.

On the first test run, `skyfield` downloads the JPL ephemeris `de421.bsp`
(~17 MB) once and caches it in `.cache/skyfield/` (not part of the git repo).
After that, everything runs offline.

## Architecture

```
nachtlotse/
├── engine/     # pure, deterministic, testable — no I/O, no network
├── data/       # persistence — sites, rigs, horizons, session log
├── weather/    # optional layer (from M4) — Open-Meteo
└── ui/         # swappable — Streamlit MVP, later Qt or web
```

Dependency direction: `ui` → `engine`/`data`. The `engine` core imports nothing
from `ui`, `data`, or `weather`.

## Tech stack

Python 3.12+ · `uv` · `skyfield` / `astroplan` / `astropy` · `pytest` · `ruff`

## License

[MIT](./LICENSE)

# Nachtlotse

*("Nachtlotse" is German for "night pilot" — like a harbor pilot who guides
ships through difficult waters, but for clear nights and telescopes.)*

> My pilot through clear nights. Answers the oldest question in astrophotography:
> **"What should I shoot tonight?"** — and delivers an honest verdict.

A deterministic session planner for astrophotography, native on macOS. It scores
tonight's sky over a given site against a given equipment rig and distills the
result down to **one** hero target plus a verdict: **GO / MARGINAL / SKIP** —
with a traceable rationale.

Motivated by [Clear Night Coach](https://clearnightcoach.com) (Windows-only).
Nachtlotse rebuilds the same core cross-platform — with an open, testable engine.

## Guiding principle

**The engine decides. An LLM formulates at most the prose — never the astronomy.**

Every altitude, every window, every framing number comes deterministically from
`skyfield`/`astroplan` against JPL ephemerides. The engine core
(`nachtlotse/engine/`) is pure Python with no UI, network, or I/O dependency, and
is fully backed by `pytest` against known astronomical values.

## Status

✅ **M0 — Scaffolding & engine core**, done.
✅ **M1 — Moon & dark window**, done.
✅ **M2 — Horizon profiles & multiple sites**, done.

- `nachtlotse/engine/models.py` — data model (`Site`, `HorizonProfile`, `Optics`,
  `Sensor`, `Mount`, `Rig`, `Target`, `Verdict`) as immutable dataclasses.
- `nachtlotse/engine/ephemeris.py` — altitude/azimuth/transit/max-altitude of a
  target via `skyfield`.
- `nachtlotse/engine/constraints.py` — astronomical-twilight dark window,
  altitude/night/moon-separation gating via `astroplan`, and horizon-profile
  clearance (`site.horizon.min_alt(az)`) via per-sample `skyfield` checks.
- `nachtlotse/data/catalog.py` — Messier core catalog (30 objects).
- `nachtlotse/data/store.py` — site persistence: name, coordinates, measured
  or sector-derived horizon profile, region, Bortle class. No location data
  ships in code — sites live entirely in a local, gitignored
  `nachtlotse/data/sites_local.yaml`. `sites_local.template.yaml` (committed)
  documents the format with two real examples; copy it to get started (see
  Quickstart below).
- `nachtlotse/cli.py` — `lotse today [--site NAME]` ranks tonight's
  *observable* targets (night + moon + altitude + horizon) by best altitude
  within the dark window; `lotse sites` lists all known sites. Rig stays
  hardcoded (ZWO Seestar S30 Pro) — multiple rigs land in M3.
- Tests against independently known astronomical/textbook values (Polaris
  altitude ≈ geographic latitude, transit altitude = 90° − lat + dec, a target
  coincident with the Moon's own position always fails separation, a
  full-circle horizon wall drops an otherwise-observable target) plus
  catalog/store/CLI smoke tests — including that the same sky yields
  different target lists at two sites with different horizons.

Not yet implemented (by design, later milestones): framing/field-rotation
constraints, multiple rigs, weather.

The full roadmap (M0–M6) and all architecture decisions are documented in
[`CLAUDE.md`](./CLAUDE.md).

## Quickstart

Requires [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync                # set up the environment + dependencies
cp nachtlotse/data/sites_local.template.yaml nachtlotse/data/sites_local.yaml
                        # then edit it: your own sites, or keep the two examples
uv run pytest          # run the tests
uv run ruff check .    # lint
uv run ruff format .   # format
uv run lotse today     # rank tonight's targets for your first site + Seestar S30 Pro
uv run lotse sites     # list all configured observing sites
```

`uv run <cmd>` runs the command inside the project's own virtual environment
(`.venv`), managed by `uv` — no need to activate it manually.

Without a `sites_local.yaml`, `lotse today`/`lotse sites` exit with a message
pointing at the template — the test suite still passes either way, since it
never depends on your local site list.

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

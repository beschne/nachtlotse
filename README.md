# Nachtlotse

*("Nachtlotse" is German for "night pilot" — like a harbor pilot who guides
ships through difficult waters, but for clear nights and telescopes.)*

> My pilot through clear nights. Answers the oldest question in astrophotography:
> **"What should I shoot tonight?"** — and delivers an honest verdict.

A deterministic session planner for astrophotography, native on macOS. It scores
tonight's sky over a given site against a given equipment rig and distills the
result down to a short, score-ranked **shortlist** of targets — each with its
own verdict: **GO / MARGINAL / SKIP** — with a traceable rationale, built on an
open, testable engine. Targets close enough to share one frame of your rig
(e.g. M81 + M82) are automatically suggested as a single co-visible group,
not two separate shortlist entries. With more than one rig configured, a
best-rig chooser can also pick whichever one frames each target best,
instead of scoring for a single rig you name. An optional nightly
briefing (Claude API, only when asked for) phrases the shortlist as
prose — the engine's numbers and verdicts still decide everything.

## Guiding principle

**The engine decides. An LLM formulates at most the prose — never the astronomy.**

Every altitude, every window, every framing number comes deterministically from
`skyfield`/`astroplan` against JPL ephemerides. The engine core
(`nachtlotse/engine/`) is pure Python with no UI, network, or I/O dependency, and
is fully backed by `pytest` against known astronomical values.

## Status

The MVP (M0–M5: engine, multi-site/multi-rig support, weather, and the
GO/MARGINAL/SKIP verdict) is done and history — development has moved on
to the roadmap beyond it. Module-by-module detail and the MVP's
milestone-by-milestone history: [STATUS.md](./STATUS.md). Current
roadmap: [ROADMAP.md](./ROADMAP.md). Architecture and all other
decisions: [CLAUDE.md](./CLAUDE.md).

## Quickstart

Requires [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync                # set up the environment + dependencies
cp nachtlotse/data/sites_local.template.yaml nachtlotse/data/sites_local.yaml
cp nachtlotse/data/rigs_local.template.yaml nachtlotse/data/rigs_local.yaml
                        # then edit both: your own sites/gear, or keep the examples
uv run pytest          # run the tests
uv run ruff check .    # lint
uv run ruff format .   # format
uv run lotse plan      # rank tonight's targets for your first site + rig
uv run lotse sites     # list all configured observing sites
uv run lotse rigs      # list all configured rigs
uv run lotse best-sky  # compare all configured sites' forecast cloud cover tonight

# --site and --rig accept a name or alias (or a unique substring of one),
# and can be combined; either defaults to the first entry in its file:
uv run lotse plan --site "Großer Feldberg" --rig S30P

# --best-rig scores every configured rig per target and keeps only the
# best-scoring one, instead of the single --rig above — useful once you
# have more than one rig and want the planner to pick. Mutually exclusive
# with --rig and --chart; doesn't group co-visible targets (see ROADMAP.md):
uv run lotse plan --best-rig

# --date plans for a given night (YYYY-MM-DD, local to the site) instead
# of tonight — useful for checking ahead. Weather beyond Open-Meteo's
# forecast horizon (16 days) shows as unavailable; the sky-geometry
# ranking and verdict still work for any date, past or future:
uv run lotse plan --site Feldberg --date 2026-11-14

# --type keeps only targets of that category (repeatable — matches any
# one of them): emission_nebula, reflection_nebula, planetary_nebula,
# dark_nebula, galaxy, galaxy_group, open_cluster, globular_cluster.
uv run lotse plan --type galaxy --type globular_cluster

# Co-visible targets (close enough to share one frame of your rig, e.g.
# M81 + M82 or the Orion Nebula complex) are folded into a single
# shortlist entry automatically — no flag needed, nothing to opt into.

# --limit caps how many catalog objects are evaluated (default: 50, use 0 for all).
# Keeps `lotse plan` fast when the catalog is large; all objects that clear
# basic constraints are still ranked, just the evaluation budget is limited:
uv run lotse plan --limit 20
uv run lotse plan --limit 0    # evaluate every catalog object

# --chart writes the shortlist's alt/az polar overview as a PNG (default
# filename: nachtlotse-shortlist.png in the current directory, overwriting
# any existing file there) — or pick your own path. Needs its own extra:
uv sync --extra charts
uv run lotse plan --chart
uv run lotse plan --chart my-plan.png

# --prose prints an LLM-written nightly briefing after the usual
# shortlist/table — phrasing only, every number/verdict still comes from
# the engine. Never called unless you pass this flag. Needs its own
# extra plus an API key; fails loudly (not silently) if either is missing:
uv sync --extra prose
export ANTHROPIC_API_KEY=sk-...
uv run lotse plan --prose

# The API key (and, optionally, which Claude model to use) can live in
# nachtlotse/data/prose_local.yaml instead of the environment variable —
# gitignored, never committed. Copy the template to create it:
cp nachtlotse/data/prose_local.template.yaml nachtlotse/data/prose_local.yaml

# best-sky answers "where's the clearest night", not "what should I shoot":
# it ranks your configured sites by forecast cloud cover in each site's own
# dark window. --radius-km restricts the comparison to sites within that
# distance of --site (default: every configured site, any distance);
# --date takes a single YYYY-MM-DD, same as `plan`, default tonight.
uv run lotse best-sky --site Feldberg --radius-km 50 --date 2026-11-14
```

`uv run <cmd>` runs the command inside the project's own virtual environment
(`.venv`), managed by `uv` — no need to activate it manually.

Without a `sites_local.yaml`/`rigs_local.yaml`, the affected commands exit
with a message pointing at the matching template — the test suite still
passes either way, since it never depends on your local site/rig lists.

On the first test run, `skyfield` downloads the JPL ephemeris `de421.bsp`
(~17 MB) once and caches it in `.cache/skyfield/` (not part of the git repo).
After that, everything runs offline.

Every Open-Meteo forecast is cached per site for 1 hour in
`.cache/open_meteo/` (also not part of the git repo) — a `plan` or
`best-sky` run within that hour reuses it instead of hitting the network
again.

## Architecture

```
nachtlotse/
├── engine/     # pure, deterministic, testable — no I/O, no network
├── data/       # persistence — sites, rigs, horizons, session log
├── weather/    # optional layer (from M4) — Open-Meteo, TTL-cached
├── charting.py # shared chart geometry, library-agnostic
├── chart_export.py  # CLI's --chart PNG export (matplotlib)
├── best_sky.py # cross-site weather comparison (`lotse best-sky`)
├── prose.py    # LLM nightly briefing (`lotse plan --prose`, opt-in)
└── cli.py      # the only front end for now — a native macOS app is
                #   planned later, kept Python-only (see CLAUDE.md)
```

Dependency direction: `cli.py` → `engine`/`data`. The `engine` core imports
nothing from `cli.py`, `data`, or `weather`.

## Tech stack

Python 3.12+ · `uv` · `skyfield` / `astroplan` / `astropy` · `pytest` · `ruff`

## License

[MIT](./LICENSE)

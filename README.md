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
✅ **M3 — Rig scoring, framing & field rotation**, done.

- `nachtlotse/engine/models.py` — data model (`Site`, `HorizonProfile`, `Optics`,
  `Sensor`, `Mount`, `Rig`, `Target`, `Verdict`) as immutable dataclasses.
  `Target.size_arcmin` carries apparent angular size for framing.
- `nachtlotse/engine/ephemeris.py` — altitude/azimuth/transit/max-altitude of a
  target via `skyfield`.
- `nachtlotse/engine/constraints.py` — astronomical-twilight dark window,
  altitude/night/moon-separation gating via `astroplan`, and horizon-profile
  clearance (`site.horizon.min_alt(az)`) via per-sample `skyfield` checks.
- `nachtlotse/engine/framing.py` — framing score (does the target's angular
  size fit the rig's field of view?) and alt-az field-rotation safety: the
  rate of change of the parallactic angle (via `astroplan`) diverges near
  the zenith, so a target an eq rig can shoot right at its peak gets pushed
  to a lower, rotation-safe moment — or excluded outright — on an alt-az
  rig. Eq mounts are never gated on this.
- `nachtlotse/data/catalog.py` — Messier core catalog (30 objects, with
  apparent sizes).
- `nachtlotse/data/store.py` — site *and rig* persistence: coordinates,
  measured/sector-derived horizon, region, Bortle class; optics/sensor/mount
  specs, plate scale, FoV. No location or equipment data ships in code —
  both live entirely in local, gitignored `sites_local.yaml` /
  `rigs_local.yaml`. The matching `*.template.yaml` files (committed)
  document the formats with real examples; copy one to get started (see
  Quickstart below). `mount.kind` is a setup choice, not a fixed hardware
  property — even an alt-az smart telescope can be wedge-mounted and
  polar-aligned for true eq tracking, so the same optics/sensor can appear
  as two separate rig entries under different aliases (e.g. `S30P` for a
  Seestar's native alt-az ball mount vs. `S30P-EQ` on a latitude wedge);
  pick per session with `--rig`.
- `nachtlotse/cli.py` — `lotse today [--site NAME] [--rig NAME]` ranks
  tonight's *observable* targets (night + moon + altitude + horizon +
  rig-aware field rotation) by best altitude within the dark window, with a
  framing-fit column; `lotse sites` / `lotse rigs` list what's configured.
  The list is sorted descending by "Max Alt" — the highest altitude each
  target safely reaches under *all* active constraints tonight, not
  necessarily its true meridian-transit altitude, so a target whose best
  window is horizon- or rotation-limited can rank below one with a lower
  transit but a cleaner shot.
- Tests against independently known astronomical/textbook values (Polaris
  altitude ≈ geographic latitude, transit altitude = 90° − lat + dec, a target
  coincident with the Moon's own position always fails separation, a
  full-circle horizon wall drops an otherwise-observable target, plate scale
  = 206.265 × pixel_um / focal_length_mm, field-rotation rate calibrated
  numerically against astroplan's own parallactic angle near vs. far from
  the zenith) plus catalog/store/CLI smoke tests — including that the same
  sky yields different target lists at two sites with different horizons,
  and that a near-zenith target is downgraded for an alt-az rig but not an
  eq one.

Not yet implemented (by design, later milestones): weather, the GO/MARGINAL/
SKIP verdict, and a "best rig for this target" chooser — `lotse today`
scores targets for whichever rig you pass, it doesn't yet pick between rigs.

The full roadmap (M0–M6) and all architecture decisions are documented in
[`CLAUDE.md`](./CLAUDE.md).

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
uv run lotse today     # rank tonight's targets for your first site + rig
uv run lotse sites     # list all configured observing sites
uv run lotse rigs      # list all configured rigs

# --site and --rig accept a name or alias (or a unique substring of one),
# and can be combined; either defaults to the first entry in its file:
uv run lotse today --site "Großer Feldberg" --rig S30P
```

`uv run <cmd>` runs the command inside the project's own virtual environment
(`.venv`), managed by `uv` — no need to activate it manually.

Without a `sites_local.yaml`/`rigs_local.yaml`, the affected commands exit
with a message pointing at the matching template — the test suite still
passes either way, since it never depends on your local site/rig lists.

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

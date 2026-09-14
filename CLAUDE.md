# Nachtlotse

> My pilot through clear nights. Answers the oldest question in astrophotography:
> **"What should I shoot tonight?"** — and delivers an honest verdict.

A deterministic session planner for astrophotography, native on macOS.
It scores tonight's sky over *your* site against *your* equipment and
distills the result down to **one** hero target plus a verdict: **GO / MARGINAL / SKIP** —
with a traceable rationale.

Modeled after [Clear Night Coach](https://clearnightcoach.com) (Windows-only).
Nachtlotse rebuilds the same core cross-platform — with an open, testable engine.

---

## Guiding principle (non-negotiable)

**The engine decides. An LLM formulates at most the prose — never the astronomy.**

Every altitude, every window, every framing number comes deterministically from the
engine (`skyfield` / `astroplan`, JPL ephemerides). Strip away the optional prose
layer and the decision stands unchanged on its own numbers. No guessing, no
fabricated facts.

Consequence for the architecture: the engine core is **pure Python, with no UI,
network, or I/O dependency**, and is fully backed by `pytest` against known values.
At a dark site, the core decision runs **offline** (weather is an optional layer).

---

## Tech stack

- **Python** 3.12+
- **Environment/deps:** `uv` (fast, reproducible) — alternatively `venv` + `pip`
- **Astronomy:** `skyfield`, `astroplan`, `astropy`, `numpy`
- **Time/zones:** `zoneinfo` (stdlib), IANA time zones
- **Weather (from M4):** Open-Meteo (free, no API key)
- **Tests:** `pytest`
- **Lint/format:** `ruff`
- **Type checking:** `mypy` (optional, recommended)
- **UI:** MVP with `streamlit` → later migration to **PySide6/Qt** (native app) or
  **FastAPI + web** (local in-browser). The UI is deliberately swappable.

---

## Architecture — three separate layers

```
nachtlotse/
├── engine/          # pure, deterministic, testable — NO I/O, NO network
│   ├── ephemeris.py     # altitude/azimuth/transit via skyfield
│   ├── constraints.py   # altitude, twilight, moon distance, horizon, framing
│   ├── framing.py       # FoV, sampling, field rotation (alt-az!)
│   ├── scoring.py       # target ranking + verdict heuristic
│   └── models.py        # dataclasses: Site, Rig, HorizonProfile, Target, Verdict
├── data/            # persistence — sites, rigs, horizons, session log
│   ├── catalog.py       # object catalog (Messier core → later expanded)
│   ├── store.py         # SQLite or YAML
│   └── hrz.py           # .HRZ import (from M2)
├── weather/         # from M4 — Open-Meteo client, cleanly separated from the core
├── ui/              # swappable — streamlit (MVP), later qt/ or web/
├── cli.py           # `lotse plan`, `lotse sites`, `lotse rigs`
└── tests/
```

**Dependency direction:** `ui` → `engine`/`data`. The `engine` core imports
*nothing* from `ui`, `data`, or `weather`. This is the most important rule in the
project.

---

## Data model (blueprint, in `engine/models.py`)

```python
@dataclass(frozen=True)
class HorizonProfile:
    # (azimuth 0..360, N=0) -> minimum altitude in degrees; interpolated linearly
    points: list[tuple[float, float]]
    def min_alt(self, az_deg: float) -> float: ...

@dataclass(frozen=True)
class Site:
    name: str
    lat_deg: float
    lon_deg: float
    elevation_m: float
    tz: str                    # IANA, e.g. "Europe/Berlin"
    horizon: HorizonProfile

@dataclass(frozen=True)
class Optics:  name: str; focal_length_mm: float; aperture_mm: float
@dataclass(frozen=True)
class Sensor:  name: str; width_px: int; height_px: int; pixel_um: float
@dataclass(frozen=True)
class Mount:   name: str; kind: Literal["altaz", "eq"]  # + optional zenith_avoid_deg

@dataclass(frozen=True)
class Rig:
    name: str
    optics: Optics
    sensor: Sensor
    mount: Mount
    # derived/computed: fov_deg, sampling_arcsec_px

@dataclass(frozen=True)
class Verdict:
    level: Literal["GO", "MARGINAL", "SKIP"]
    reasons: list[str]         # every number comes from the engine
```

**First rig (reference case):** ZWO Seestar S30 Pro — focal length/sensor as
presets, **alt-az mount** ⇒ field rotation is real and gets scored.

---

## Coding conventions

- Full **type hints**; `ruff` and (recommended) `mypy` must pass cleanly.
- Engine functions are **pure**: same input → same output, no side effects.
- **No magic in the core:** no hidden defaults for site/rig — everything is
  passed explicitly (as in the model: "it won't guess any of it").
- All numbers carry a **unit in the name** (`focal_length_mm`, `alt_deg`, `sep_deg`).
- Time is **always** timezone-aware (`aware datetime`), UTC internally, local TZ
  only at the UI boundary.
- Every new constraint / scoring rule ships **with a test** against a known value.
- Small, thematic commits; one milestone = one branch.

---

## MVP roadmap (milestones, complete)

Follow the order strictly — each stage builds on the previous one, and the engine
core grows before the UI is added.

### M0 — Scaffolding & engine core *(target: one weekend)*
- Project setup: `uv`, `ruff`, `pytest`, directory structure.
- Data model (dataclasses). **One** site (Bad Homburg) and **one** rig (Seestar
  S30 Pro), hardcoded.
- Engine: altitude/azimuth/transit time of a target via `skyfield`.
- Small catalog (Messier core, ~30 objects). Ranking by max altitude within the
  time window.
- CLI: `lotse plan` prints top targets as a table.
- **DoD:** tests compare altitude/transit against known ephemeris values
  (± tolerance).

### M1 — Moon & dark window
- Astronomical twilight (the window in which photography is worthwhile).
- Moon phase, moon altitude, moon separation as constraints.
- `astroplan`: `AltitudeConstraint`, `AtNightConstraint`, `MoonSeparationConstraint`,
  `observability_table()`.
- **DoD:** a target near a full moon/the horizon correctly drops out of the ranking.

### M2 — Horizon profiles & multiple sites
- Custom `HorizonConstraint` (target visible only if `alt > horizon.min_alt(az)`).
- `.HRZ` import (simple text format). Blocked targets are no longer suggested.
- Persistence for multiple sites (SQLite/YAML) + CLI `lotse sites`.
- **DoD:** the same sky yields different target lists at two sites with different
  horizons.

### M3 — Rig scoring, framing & field rotation
- FoV and sampling (arcsec/px) from optics + sensor. Framing score: does the
  target fit the sensor?
- **Alt-az field rotation** from the parallactic angle (`astroplan` provides it);
  divergence near the zenith ⇒ penalty/exclusion (the "mount limits near zenith"
  criterion).
- Multiple rigs; scoring picks the best target-rig combination or scores per rig.
- CLI `lotse rigs`.
- **DoD:** a near-zenith target is penalized for the alt-az mount, but not for a
  (hypothetical) eq rig.

### M4 — Weather & verdict
- Open-Meteo client (clouds, wind, humidity, dew point) for the dark window.
- Heuristic ⇒ **GO / MARGINAL / SKIP** with a list of reasons.
- Weather stays an **optional layer**; without a network, the core still returns
  the target ranking.
- **DoD:** overcast sky ⇒ SKIP with a stated reason; clear window with a low
  target ⇒ MARGINAL.
- *Note:* the weighting (clouds vs. moon vs. altitude vs. rotation) is subjective
  and gets **tuned iteratively** — this is where the real thinking happens, not
  in the physics.

### M5 — UI (Streamlit MVP)
- Verdict light, hero target + backups, altitude curve over the night, rationale.
- Site/rig selection. Later migration to Qt or FastAPI+web.
- **DoD:** a single glance is enough to decide, without opening the CLI.

The MVP (M0–M5) is complete.

---

## Roadmap

Ideas for after the MVP, in priority order:

1. With all three book imports done (Kier, Bracken's *Astrophotography
   Planner*, and his *Astrophotography Sky Atlas*), the accumulated skip
   list is large enough to analyze rather than just carry forward: the
   large majority — diffuse emission/dark nebulae and Abell planetary
   nebulae without a published integrated magnitude, and cases where the
   only found magnitude belongs to an illuminating star or a sub-feature
   rather than the pictured object — is a structural gap in what ever gets
   photometered at the object level, not a temporary data-search gap, and
   isn't expected to resolve with more searching. Worth revisiting only
   the handful of cases where the *designation itself*, not just its
   magnitude, is in question and a future SIMBAD/NED correction could
   settle it: IC 4606 ("Antares Nebula"), IC 1316, NGC 1555 ("Hind's
   Variable Nebula"), NGC 6874, and Simeis 147. See
   [SKIPPED-OBJECTS.md](./SKIPPED-OBJECTS.md) for the full list and
   reasoning behind each exclusion.
2. Streamlit UI: clicking a backup target shows the same detail panel as the
   hero (stats + altitude curve).
3. Streamlit UI: a real RGB/visual image of the hero target (e.g. from an
   image survey), cached locally rather than refetched on every rerun.
4. Current events: well-placed comets, supernova alerts; later also minor
   planets/asteroids and near-Earth objects (NEOs).
5. A "best rig for this target" chooser — `lotse plan` scores targets for
   whichever rig you pass, it doesn't yet pick between rigs.
6. Session log: record what's already been captured, and when — total
   exposure time per target, logged per session. Prior exposure on a target
   is informational, not a deterrent; it doesn't mean the target drops out of
   contention, more can still be worth shooting. No attached photos.
7. Optional LLM prose (nightly briefing) via the Claude API — numbers strictly
   from the engine, never computed by the LLM.

### Possible future extensions (not scheduled)
- Export today's pick to a NINA-compatible format.
- Streamlit UI: gray out the sidebar's "Apply" button once its values are
  applied, re-enabling it only on the next edit. Not solvable with the
  current `st.form` batching (widgets inside a form don't trigger a rerun
  when touched, so there's no rerun to notice a value changed and re-enable
  the button until you already clicked Apply again) — would need giving up
  batched apply for per-change live reactivity instead. Parked for now.

### Out of scope (deliberately excluded)
- Mount control / session automation
- Cloud sync
- Accounts
- Southern-sky curation
- Mobile apps

Deliberately excluded; not reconsidered above without a specific reason to.

---

## Anthropic LLM recommendation (for development with Claude Code)

- **Default: Claude Sonnet 5.** The workhorse for agentic coding — fast, strong,
  cost-efficient across many iteration rounds. Right for 90% of sessions.
- **For the hard problems: Claude Opus 5.** Architecture decisions, the
  verdict/field-rotation heuristic, tougher debugging. Switch via `/model` in
  Claude Code.
- **For trivial or bulk changes: Claude Haiku 4.5**, when speed/cost matter.
- **Rule of thumb:** Sonnet 5 as default, switch on Opus 5 as soon as a session
  gets think-heavy instead of type-heavy.

The optional **LLM prose extension** (see "Roadmap") would
call the Claude API (e.g. `claude-sonnet-5`) — only for phrasing, never for
computing.

---

## Useful commands

```bash
uv sync                       # environment/dependencies
uv run pytest                 # tests
uv run ruff check .           # lint
uv run ruff format .          # format
uv run lotse plan              # tonight's recommendation (from M0)
uv run streamlit run ui/app.py  # UI (from M5)
```

---

## Starting point for Claude Code

Start with **M0**. First lay down the data model (`engine/models.py`) and an
ephemeris test, then write `ephemeris.py` to satisfy it (TDD). Only once
`lotse plan` produces a plausible, tested target list for Bad Homburg with the
Seestar S30 Pro rig, move on to M1.

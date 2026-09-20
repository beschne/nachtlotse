# Nachtlotse

> My pilot through clear nights. Answers the oldest question in astrophotography:
> **"What should I shoot tonight?"** — and delivers an honest verdict.

A deterministic session planner for astrophotography, native on macOS.
It scores tonight's sky over *your* site against *your* equipment and
distills the result down to a short, score-ranked shortlist of targets —
each with its own verdict: **GO / MARGINAL / SKIP** — and a traceable
rationale, built on an open, testable engine.

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
- **Type checking:** `mypy` (recommended; not currently in `pyproject.toml` —
  add it before relying on it)
- **UI:** the CLI is the only front end for now. A Streamlit MVP (M5) was
  built and later retired — maintaining two front ends against the same
  engine wasn't worth it while the CLI is still the active focus. The
  longer-term goal is a **native macOS app, in Python** (Swift is
  explicitly out of scope; exact toolkit — e.g. PySide6/Qt — not yet
  decided) — see "Roadmap".

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
│   ├── catalog/         # object catalog, YAML files banded by magnitude
│   │                     (mag_lt_6.yaml … mag_15_16.yaml) — Messier core
│   │                     plus the Kier/Bracken book imports
│   └── store.py         # sites_local.yaml / rigs_local.yaml (gitignored,
│                          committed .template.yaml alongside each); horizon
│                          profiles are azimuth→min-altitude points inline
│                          in site YAML, no separate .HRZ import
├── weather/         # from M4 — Open-Meteo client, cleanly separated from the core
├── charting.py      # shared polar-chart geometry, no charting-library dependency
├── chart_export.py  # `lotse plan --chart`'s PNG export (matplotlib)
├── cli.py           # `lotse plan`, `lotse sites`, `lotse rigs` — the only front end
└── tests/
```

**Dependency direction:** `cli.py` → `engine`/`data`. The `engine` core imports
*nothing* from `cli.py`, `data`, or `weather`. This is the most important rule in
the project — whatever front end comes next (see "Roadmap") plugs in the same way.

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

# A target can carry more than one type (M42 is emission + reflection).
TargetType = Literal[
    "emission_nebula", "reflection_nebula", "planetary_nebula", "dark_nebula",
    "galaxy", "galaxy_group", "open_cluster", "globular_cluster",
]
TARGET_TYPE_LABELS: dict[TargetType, str]  # shared display labels

@dataclass(frozen=True)
class Target:
    name: str
    ra_deg: float
    dec_deg: float
    catalog_id: str = ""
    aliases: tuple[str, ...] = ()          # other designations, e.g. M31 -> "NGC 224"
    size_arcmin: tuple[float, float] = (0.0, 0.0)  # (0.0, 0.0) = unknown
    magnitude: float | None = None         # None = no reliably sourced value
    types: tuple[TargetType, ...] = ()

@dataclass(frozen=True)
class WeatherSummary:
    # aggregated over the observing window; optional engine.scoring input —
    # the engine core never fetches this itself
    max_cloud_cover_pct: float
    avg_cloud_cover_pct: float
    max_wind_kmh: float
    min_dew_point_spread_c: float

@dataclass(frozen=True)
class Verdict:
    level: Literal["GO", "MARGINAL", "SKIP"]
    reasons: list[str]         # every number comes from the engine
    # one Verdict per shortlisted target, not one per night — see roadmap
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
- **Catalog data sourcing:** when looking up SIMBAD/NED for catalog entries,
  query sequentially, not in parallel — parallel requests reliably time out.
  Be skeptical of an AI-summarized page when it contradicts prior research
  or general astronomical knowledge (a SIMBAD fetch once claimed "IC 1316 =
  NGC 6901, a barred spiral galaxy", fabricated by the summarizing step —
  NED, checked directly, still showed "nothing here, nominal position" as
  it always had); cross-check surprising findings against a second source
  before trusting them. When two sourced values for the same object
  disagree by **less than 1.0 mag**, that's not a blocker — note both
  values as a comment next to the entry, with their sources, and use the
  better-sourced one as the actual field value. A gap of 1.0 mag or more is
  a real conflict to resolve or flag explicitly, not just document.

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
- Horizon profile as azimuth→min-altitude points, inline in site YAML.
  Blocked targets are no longer suggested.
- Persistence for multiple sites (YAML) + CLI `lotse sites`.
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
- Site/rig selection.
- **DoD:** a single glance is enough to decide, without opening the CLI.
- *Later retired:* once the shortlist replaced the single hero target, the
  UI needed its own copy of every new rendering (e.g. the polar chart got
  built twice — once in Altair for Streamlit, once in matplotlib for the
  CLI's `--chart`) just to keep two front ends in sync. With Nachtlotse
  staying a personal/portfolio project and a native macOS app the real
  long-term goal (Python, not Swift — see "Roadmap"), that double
  maintenance wasn't worth it, so the Streamlit UI was removed and the CLI
  is the only front end again.

The MVP (M0–M5) is complete.

---

## Roadmap

Ideas for after the MVP, in priority order:

1. **Object count limit:** computing scores for every catalog object takes too
   long. Limit the set of considered objects and output only a limited number
   by default. The limit should be configurable (CLI flag) up to all objects.
   This is a performance prerequisite for all future work — the planning step
   must be fast enough to make iterative development tolerable.
2. **Multi-object grouping:** the current planner scores individual targets in
   isolation. With widefield gear (Seestar S30 Pro at 300 mm), multiple objects
   often fit the sensor simultaneously. The planner should detect when targets
   are close enough to share the same field of view (e.g. LBN 550 + 552 + 555,
   NGC 2244 + 2624, M81 + M82) and suggest them as co-visible groups. This
   requires angular-separation checks between catalog objects and a grouping
   heuristic.
3. **Session log:** record what's already been captured, and when — total
   exposure time per target, logged per session. Prior exposure on a target
   is informational, not a deterrent; it doesn't mean the target drops out of
   contention, more can still be worth shooting. No attached photos.
4. **Best-rig chooser:** `lotse plan` scores targets for whichever rig you pass,
   it doesn't yet pick between rigs. `framing_score`
   (`engine/framing.py`) now scales with fill fraction (1.0 at a fill
   fraction of 1.0, fading toward 0.0 as the target shrinks toward a speck
   or, past 1.0, as it clips) instead of the old flat 20%-100% plateau, so
   the gradient a chooser needs — preferring the more format-filling rig,
   not just any non-clipping one — is in place. The chooser itself (picking
   between rigs, not just scoring one) is still to build.
5. **LLM prose (nightly briefing)** via the Claude API — numbers strictly from
   the engine, never computed by the LLM. No longer optional; this is the
   presentation layer that wraps the engine's numbers in readable prose.
6. **Current events:** well-placed comets, supernova alerts; later also minor
   planets/asteroids and near-Earth objects (NEOs).
7. **Native macOS app** — the long-term UI goal now that Nachtlotse's GitHub
   presence is explicitly a portfolio piece, not just a personal tool.
   Python throughout (Swift is deliberately out of scope); exact toolkit
   undecided (PySide6/Qt is the leading candidate) — to be designed once
   the CLI's own feature set (items above) has matured further. Whatever
   it consumes — `--json` output, or the engine/`planning` layer directly
   if it's Python-native — the same `cli.py` → `engine`/`data` dependency
   direction applies; see the Streamlit MVP's retirement (M5, above) for
   why this project doesn't maintain two front ends at once.
8. **Structured `lotse plan --json` output**, alongside the existing
   human-readable table (not replacing it) — the interface a future native
   app, or any other tooling, consumes instead of parsing text output.
   Straightforward: `NightPlan`/`ShortlistEntry`/`RankedTarget` are already
   plain dataclasses/NamedTuples, so this is a serializer in `cli.py`, not
   an engine change.

### Possible future extensions (not scheduled)
- Export today's pick to a NINA-compatible format.
- Multilingual UI/CLI text (at minimum German and English). Everything
  user-facing is English-only for now; this stays parked until there's a
  reason to localize.

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
uv sync --extra charts         # + matplotlib, needed for `lotse plan --chart`
uv run pytest                 # tests
uv run ruff check .           # lint
uv run ruff format .          # format
uv run lotse plan              # tonight's recommendation (from M0)
uv run lotse plan --limit 20   # evaluate only the first 20 matching objects
uv run lotse plan --limit 0    # evaluate all catalog objects
uv run lotse plan --chart      # + the shortlist's polar chart as a PNG
```

---

## Starting point for Claude Code

Start with **M0**. First lay down the data model (`engine/models.py`) and an
ephemeris test, then write `ephemeris.py` to satisfy it (TDD). Only once
`lotse plan` produces a plausible, tested target list for Bad Homburg with the
Seestar S30 Pro rig, move on to M1.

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
  longer-term goal is a **native macOS app, in Python, on PySide6/Qt**
  (Swift is explicitly out of scope; PySide6 was chosen over PyObjC/AppKit
  after a hands-on side-by-side spike — see [ROADMAP.md](./ROADMAP.md)).

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
the project — whatever front end comes next (see [ROADMAP.md](./ROADMAP.md)) plugs
in the same way.

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

M0–M5 (scaffolding & engine core, moon & dark window, horizon profiles &
multiple sites, rig scoring/framing/field rotation, weather & verdict, and
a since-retired Streamlit UI) are all complete. For the detailed
milestone-by-milestone breakdown (scope, DoD per milestone, and the note
on why the Streamlit UI was retired), see
[STATUS.md](./STATUS.md#mvp-roadmap-milestones-detail).

---

## Roadmap

Tracked separately in [ROADMAP.md](./ROADMAP.md): the prioritized list of
ideas for after the MVP, and what's deliberately out of scope. Update
that file, not this one, when roadmap items are added, reprioritized, or
closed.

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

`lotse plan --prose`'s nightly briefing (`nachtlotse/prose.py`) calls the
Claude API (`claude-sonnet-5`) — only for phrasing, never for computing, and
only when `--prose` is explicitly passed (see STATUS.md).

---

## Useful commands

```bash
uv sync                       # environment/dependencies
uv sync --extra charts         # + matplotlib, needed for `lotse plan --chart`
uv sync --extra prose          # + anthropic, needed for `lotse plan --prose`
uv sync --extra gui            # + PySide6, needed for `lotse gui` (early, in progress)
uv run pytest                 # tests
uv run ruff check .           # lint
uv run ruff format .          # format
uv run lotse plan              # tonight's recommendation (from M0)
uv run lotse plan --limit 20   # evaluate only the first 20 matching objects
uv run lotse plan --limit 0    # evaluate all catalog objects
uv run lotse plan --chart      # + the shortlist's polar chart as a PNG
uv run lotse plan --prose      # + an LLM-written nightly briefing (needs ANTHROPIC_API_KEY)
uv run lotse gui                # the early native GUI (see ROADMAP.md)
```

---

## Starting point for Claude Code

Start with **M0**. First lay down the data model (`engine/models.py`) and an
ephemeris test, then write `ephemeris.py` to satisfy it (TDD). Only once
`lotse plan` produces a plausible, tested target list for Bad Homburg with the
Seestar S30 Pro rig, move on to M1.

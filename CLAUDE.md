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
- **UI:** `streamlit`. The UI layer is deliberately swappable (e.g. a
  **FastAPI + web** front end, if a browser-based UI is ever wanted), but a
  native **PySide6/Qt** app is not planned — see "Possible future
  extensions (not scheduled)".

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
├── ui/              # swappable — streamlit; a future web/ front end stays open
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

# A target can carry more than one type (M42 is emission + reflection).
TargetType = Literal[
    "emission_nebula", "reflection_nebula", "planetary_nebula", "dark_nebula",
    "galaxy", "galaxy_group", "open_cluster", "globular_cluster",
]
TARGET_TYPE_LABELS: dict[TargetType, str]  # shared CLI/UI display labels

@dataclass(frozen=True)
class Target:
    name: str
    ra_deg: float
    dec_deg: float
    catalog_id: str = ""
    aliases: tuple[str, ...] = ()          # other designations, e.g. M31 -> "NGC 224"
    size_arcmin: tuple[float, float] = (0.0, 0.0)  # (0.0, 0.0) = unknown
    magnitude: float = 99.0                # 99.0 = unknown, sorts as faintest
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

The MVP (M0–M5) is complete.

---

## Roadmap

Ideas for after the MVP, in priority order:

1. New: a polar (alt/az) chart as the entry point into a shortlist —
   azimuth around the ring, altitude (or zenith distance) as the radius,
   with **all** shortlisted objects' tracks over the dark window plotted on
   it together (one line per object, distinguishable by color/label), not
   one chart per object. The horizon-blocked region is drawn as a
   grayed-out wedge straight from `HorizonProfile.min_alt(az)` — no new
   astronomy, just a second, more informative rendering of numbers the
   engine already produces (today's `_altitude_chart` only plots one
   shortlisted target's altitude over time as a line, with no azimuth/
   horizon context). There is exactly one polar chart — the shortlist
   overview. The per-object detail view (roadmap item 5) is not polar;
   it's the existing altitude-over-time line chart, just scoped to
   whichever object was clicked instead of always the top pick.
2. Streamlit UI: swap the object-type `st.multiselect` (`app.py`'s
   `selected_types`, currently empty = no filter) for one checkbox per
   `TargetType`, all checked by default — filtering out a category becomes
   an explicit uncheck instead of an opt-in multiselect.
3. With all three book imports done (Kier, Bracken's *Astrophotography
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
4. Decide how to handle visually attractive objects that don't have a
   clear, published integrated magnitude — the structural gap identified
   in item #3's skip-list review, but a design question of its own rather
   than more data-searching. Right now `Target.magnitude` defaults to 99.0,
   which sorts/filters an unknown-magnitude object as if arbitrarily faint,
   so a real showpiece can drop out of contention entirely just for lacking
   a number, not for being unsuitable. Not decided yet: whether to admit a
   curated subset with an editorial best-estimate magnitude, add a
   framing/size-only ranking path that never needs magnitude, or accept the
   exclusion as-is for objects with no reliable number at all.
5. Streamlit UI: clicking a shortlisted target shows the same detail panel
   (stats + altitude-over-time curve) as the top pick.
6. Streamlit UI: a real RGB/visual image of a shortlisted target (e.g. from
   an image survey), cached locally rather than refetched on every rerun.
7. Current events: well-placed comets, supernova alerts; later also minor
   planets/asteroids and near-Earth objects (NEOs).
8. A "best rig for this target" chooser — `lotse plan` scores targets for
   whichever rig you pass, it doesn't yet pick between rigs.
9. Session log: record what's already been captured, and when — total
   exposure time per target, logged per session. Prior exposure on a target
   is informational, not a deterrent; it doesn't mean the target drops out of
   contention, more can still be worth shooting. No attached photos.
10. Optional LLM prose (nightly briefing) via the Claude API — numbers strictly
    from the engine, never computed by the LLM.

### Possible future extensions (not scheduled)
- A native **PySide6/Qt** UI. Only ever motivated by shipping a
  distributable native app; Nachtlotse is a personal tool + portfolio
  project rather than a product, so that motivation doesn't apply, and
  `streamlit` stays the UI. Revisit only if that framing changes.
- Export today's pick to a NINA-compatible format.
- Streamlit UI: gray out the sidebar's "Apply" button once its values are
  applied, re-enabling it only on the next edit. Not solvable with the
  current `st.form` batching (widgets inside a form don't trigger a rerun
  when touched, so there's no rerun to notice a value changed and re-enable
  the button until you already clicked Apply again) — would need giving up
  batched apply for per-change live reactivity instead. Parked for now.
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
uv sync --extra ui             # + streamlit, needed for the UI below
uv run pytest                 # tests
uv run ruff check .           # lint
uv run ruff format .          # format
uv run lotse plan              # tonight's recommendation (from M0)
uv run streamlit run nachtlotse/ui/app.py  # UI (from M5)
```

---

## Starting point for Claude Code

Start with **M0**. First lay down the data model (`engine/models.py`) and an
ephemeris test, then write `ephemeris.py` to satisfy it (TDD). Only once
`lotse plan` produces a plausible, tested target list for Bad Homburg with the
Seestar S30 Pro rig, move on to M1.

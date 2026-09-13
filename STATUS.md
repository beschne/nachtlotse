# Status

Detailed implementation status, module by module. For the milestone overview
and roadmap, see [README.md](./README.md) and [CLAUDE.md](./CLAUDE.md).

## Milestones

- ✅ **M0 — Scaffolding & engine core**, done.
- ✅ **M1 — Moon & dark window**, done.
- ✅ **M2 — Horizon profiles & multiple sites**, done.
- ✅ **M3 — Rig scoring, framing & field rotation**, done.
- ✅ **M4 — Weather & verdict**, done.
- ✅ **M5 — UI (Streamlit MVP)**, done.

## `nachtlotse/engine/models.py`

- Data model (`Site`, `HorizonProfile`, `Optics`, `Sensor`, `Mount`, `Rig`,
  `Target`, `Verdict`) as immutable dataclasses.
- `Target.size_arcmin` carries apparent angular size for framing.

## `nachtlotse/engine/ephemeris.py`

- Altitude/azimuth/transit/max-altitude of a target via `skyfield`.
- `altitude_series`: altitude/azimuth at N evenly spaced points across a
  window, vectorized through skyfield rather than looped — the night-long
  curve the UI plots, not a constraint check.

## `nachtlotse/engine/constraints.py`

- Astronomical-twilight dark window, altitude/night/moon-separation gating
  via `astroplan`.
- Horizon-profile clearance (`site.horizon.min_alt(az)`) via per-sample
  `skyfield` checks.

## `nachtlotse/engine/framing.py`

- Framing score: does the target's angular size fit the rig's field of view?
- `target_priority_score`: combines altitude and framing score into the
  actual ranking key `planning.rank_targets` sorts by — multiplicative
  (`altitude/90 × fit`), so a poor fit vetoes a target regardless of how
  high it sits, rather than needing a second tunable weight alongside
  altitude. Reduces to plain altitude for the common case (`fit == 1.0`).
- Alt-az field-rotation safety: the rate of change of the parallactic angle
  (via `astroplan`) diverges near the zenith, so a target an eq rig can shoot
  right at its peak gets pushed to a lower, rotation-safe moment — or
  excluded outright — on an alt-az rig. Eq mounts are never gated on this.
- `photographic_limiting_magnitude`: a rough, explicitly tunable estimate of
  the faintest magnitude a stacked session can reach, from aperture + Bortle
  class (`lotse rigs` shows it for Bortle 2 and 5) — computed live, not
  stored, so it can't go stale when the underlying constant gets tuned. Not
  yet wired into catalog filtering; today it's informational only.

## `nachtlotse/data/catalog/`

- Deep-sky catalog: 88 curated objects (30 Messier, 58 NGC/IC — well-known
  astrophotography targets with no Messier number, e.g. North America
  Nebula, Veil Nebula, Helix Nebula, Antennae Galaxies).
- Sourced against [OpenNGC](https://github.com/mattiaverga/OpenNGC)
  (CC-BY-SA-4.0) rather than memory alone once objects got obscure enough
  that misremembering a magnitude was a real risk.
- Magnitudes prefer OpenNGC's B-Mag field over V-Mag (an early extraction
  pass that preferred V-Mag whenever present produced silently wrong
  values, e.g. the Sculptor Galaxy's V-Mag=11.11 vs. its correct
  B-Mag≈7.9; fixed with a "prefer B, fall back to V" rule with an anomaly
  guard).
- Curation stops at objects OpenNGC tags with a real common name — reaching
  down to ~mag 12.9 (e.g. Little Ghost Nebula); going deeper still would
  mean pulling in anonymous, rarely imaged galaxies mostly known by
  catalog number alone, which stretches "well-known target" past what a
  name-only human curation pass can vouch for.
- Split into `mag_*.yaml` files by apparent magnitude, not by source
  catalog — a bin file doesn't care whether an object is Messier, NGC, or
  IC, and a site+rig's computed limiting magnitude will eventually be able
  to load only the bins it needs.
- Every physical object gets exactly one `Target` entry regardless of how
  many catalogs list it — `Target.aliases` carries the others (e.g. M31's
  `aliases=("NGC 224",)`; M16's Eagle Nebula carries both `NGC 6611` and
  `IC 4703`, its two other designations), so the same object can never show
  up twice under two different names.
- Two policy tests keep every entry within scope: declination ≥ −30°
  (reaches ≥20° altitude from any "40°N or further north" site — M83 at
  −29.87° is the existing edge case that pins this boundary) and magnitude
  ≤ 18.6 (this project's widest aperture, Redcat 51, under its darkest sky
  in scope, Bortle 2) — the catalog is well within that ceiling today, so
  there's room to go deeper later without hitting it.

## `nachtlotse/planning.py`

- Sits between the pure `engine` core and any UI: `plan_night(site, rig,
  when)` runs the whole pipeline — dark window, moon illumination, ranked
  targets (`rank_targets`, rig-aware field-rotation gating included),
  weather (`fetch_weather_summary`, optional and network-only here), and
  the hero verdict — into one `NightPlan`. Extracted out of `cli.py` when
  the Streamlit UI needed the exact same pipeline, so neither front end
  duplicates it; `cli.py` and `nachtlotse/ui/app.py` both just format a
  `NightPlan` for their own medium.
- Not UI code itself — no printing, no framework imports — which is what
  keeps it shared instead of becoming a third implementation.

## `nachtlotse/data/store.py`

- Site *and* rig persistence: coordinates, measured/sector-derived horizon,
  region, Bortle class; optics/sensor/mount specs, plate scale, FoV.
- No location or equipment data ships in code — both live entirely in
  local, gitignored `sites_local.yaml` / `rigs_local.yaml`. The matching
  `*.template.yaml` files (committed) document the formats with real
  examples; copy one to get started (see the Quickstart in README.md).
- `mount.kind` is a setup choice, not a fixed hardware property — even an
  alt-az smart telescope can be wedge-mounted and polar-aligned for true eq
  tracking, so the same optics/sensor can appear as two separate rig
  entries under different aliases (e.g. `S30P` for a Seestar's native
  alt-az ball mount vs. `S30P-EQ` on a latitude wedge); pick per session
  with `--rig`.

## `nachtlotse/weather/open_meteo.py`

- The one module allowed to touch the network: a free, no-key Open-Meteo
  client (clouds, wind, humidity, dew point) for a site's dark window.
- Optional by design — any failure (offline, bad response) raises
  `WeatherUnavailable`, which the CLI turns into "Weather: unavailable"
  rather than a crash; the ranking keeps working from sky geometry alone.

## `nachtlotse/engine/scoring.py`

- The GO/MARGINAL/SKIP verdict for the hero (top-ranked) target: pure and
  deterministic given an altitude plus an optional `WeatherSummary`, so it
  never touches the network itself.
- Cloud cover, wind, dew-point margin, and low altitude can each downgrade
  the verdict, worst-wins; thresholds are named module constants, called
  out as a tunable heuristic rather than physics (per CLAUDE.md's M4 note).
- A missing forecast (`weather=None`) also caps the verdict at MARGINAL —
  GO always means "cloud/wind/dew forecast checked and clear", never "sky
  geometry looked fine and we couldn't check the rest".

## `nachtlotse/cli.py`

- `lotse plan [--site NAME] [--rig NAME] [--date YYYY-MM-DD]` calls
  `planning.plan_night` and prints the result: dark window, moon
  illumination, weather summary, a framing-fit column, and a
  GO/MARGINAL/SKIP verdict for the top target; `lotse sites` / `lotse rigs`
  list what's configured.
- The ranked list is sorted by `framing.target_priority_score` (altitude ×
  framing fit, descending) — the "Max Alt" column alone no longer decides
  the order. A target whose best window is horizon- or rotation-limited
  can already rank below one with a lower transit but a cleaner shot; a
  target that barely fits the frame (e.g. a small planetary nebula on a
  wide-field rig) is now deprioritized the same way, instead of winning
  hero status purely for sitting high in the sky.

## `nachtlotse/ui/app.py`

- The M5 Streamlit MVP: same rule as the CLI — it calls `planning.plan_night`
  for every number on the page and adds no astronomy of its own. An
  optional extra (`uv sync --extra ui`), not a core dependency, in keeping
  with "the UI is deliberately swappable" (CLAUDE.md).
- Sidebar: site/rig selection (from the same local YAML as the CLI) plus a
  date picker; `st.cache_data` keys the plan on (site, rig, date) so
  switching between them doesn't re-run the ephemeris/weather pipeline for
  a combination already seen this session.
- Main page, single glance: a colored verdict box (`st.success` /
  `st.warning` / `st.error` map directly onto GO / MARGINAL / SKIP) with
  its reasons listed underneath, the hero target's stats, an altitude
  curve for the hero across the whole dark window (`ephemeris.
  altitude_series`, with the 20° minimum-useful-altitude line for
  reference), and a backups table of the next several ranked targets.
- Missing `sites_local.yaml`/`rigs_local.yaml` shows the same actionable
  setup hint as the CLI (`store.require_sites`/`require_rigs`) rather than
  a raw traceback.

## Tests

- Against independently known astronomical/textbook values: Polaris
  altitude ≈ geographic latitude, transit altitude = 90° − lat + dec, a
  target coincident with the Moon's own position always fails separation, a
  full-circle horizon wall drops an otherwise-observable target, plate
  scale = 206.265 × pixel_um / focal_length_mm, field-rotation rate
  calibrated numerically against astroplan's own parallactic angle near vs.
  far from the zenith.
- Plus catalog/store/CLI smoke tests — including that the same sky yields
  different target lists at two sites with different horizons, a
  near-zenith target is downgraded for an alt-az rig but not an eq one,
  overcast sky yields SKIP with the cloud cover named as the reason, and a
  clear window with a low target yields MARGINAL.
- The weather client's own tests mock `urllib.request.urlopen` — like the
  rest of the suite, they never touch the real network.
- The Streamlit UI is tested with streamlit's own `AppTest` harness — runs
  the real script in a simulated session (no browser) and asserts on its
  element tree, so a broken import or a bad `st.*` call fails the suite
  the same way a broken `lotse plan` would. Skips itself (`pytest.
  importorskip`) when the `ui` extra isn't installed, since streamlit
  isn't a core dependency.

## Not yet implemented (by design)

A "best rig for this target" chooser — `lotse plan` scores targets for
whichever rig you pass, it doesn't yet pick between rigs. M6 (comfort &
prose) is documented in [CLAUDE.md](./CLAUDE.md).

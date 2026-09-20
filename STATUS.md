# Status

Milestone overview and detailed implementation status, module by module.
For architecture and conventions, see [CLAUDE.md](./CLAUDE.md); for the
full roadmap, see [ROADMAP.md](./ROADMAP.md).

## Milestones

- ✅ **M0 — Scaffolding & engine core**, done.
- ✅ **M1 — Moon & dark window**, done.
- ✅ **M2 — Horizon profiles & multiple sites**, done.
- ✅ **M3 — Rig scoring, framing & field rotation**, done.
- ✅ **M4 — Weather & verdict**, done.
- ✅ **M5 — UI (Streamlit MVP)**, done, later retired — see this file's M5
  note below and [ROADMAP.md](./ROADMAP.md) (native macOS app, Python-only).

## `nachtlotse/engine/models.py`

- Data model (`Site`, `HorizonProfile`, `Optics`, `Sensor`, `Mount`, `Rig`,
  `Target`, `Verdict`) as immutable dataclasses.
- `Target.size_arcmin` carries apparent angular size for framing.
- `Target.magnitude: float | None` — `None` means no reliably sourced
  integrated magnitude exists for the object at all (most diffuse
  emission/dark nebulae and Abell planetary nebulae never get one; see
  SKIPPED-OBJECTS.md), not "arbitrarily faint". Same convention as
  `size_arcmin == (0.0, 0.0)` for unknown size — an editorial guessed
  magnitude was rejected as exactly the "fabricated fact" the Guiding
  Principle rules out.
- `Target.types`: one or more of `TargetType` (emission/reflection/
  planetary/dark nebula, galaxy, galaxy group, open/globular cluster), with
  a shared `TARGET_TYPE_LABELS` display-name map so every front end spells
  a category the same way. An object can carry more than one (M42 is both
  an emission and a reflection nebula).

## `nachtlotse/engine/ephemeris.py`

- Altitude/azimuth/transit/max-altitude of a target via `skyfield`.
- `altitude_series`: altitude/azimuth at N evenly spaced points across a
  window, vectorized through skyfield rather than looped — the night-long
  curve `charting.shortlist_tracks` plots, not a constraint check.

## `nachtlotse/engine/constraints.py`

- Astronomical-twilight dark window, altitude/night/moon-separation gating
  via `astroplan`.
- Horizon-profile clearance (`site.horizon.min_alt(az)`) via per-sample
  `skyfield` checks.

## `nachtlotse/engine/framing.py`

- Framing score: does the target's angular size fit the rig's field of view?
- `surface_brightness_mag_arcsec2`: a target's integrated magnitude spread
  over its actual angular area (μ = m + 2.5·log₁₀(area_arcsec²)) — checked
  against hand calculations for M57 (~17.79, published ~18.1) and NGC 7000
  (~22.83, published ~22). The real signal for ranking extended objects:
  a small bright planetary nebula packs far more light per pixel than a
  much larger, fainter-per-pixel object at the same integrated magnitude.
- `reach_factor`: compares a target's surface brightness against
  `sky_brightness_mag_arcsec2` (below) plus a tunable stacking margin
  (`DEFAULT_STACKING_MARGIN_MAG`) — 1.0 (unconstrained) when magnitude,
  size, or the site's sky brightness isn't known, fading toward (never
  fully to) a floor otherwise. Downgrades, never excludes outright — the
  estimate carries real uncertainty of its own.
- `sky_brightness_mag_arcsec2`: a site's zenith, new-moon sky darkness — a
  real SQM measurement (`Site.zenith_sky_brightness_mag_arcsec2`) if
  documented, otherwise a Bortle-class estimate (`Site.bortle_class`,
  interpolated the same way as `photographic_limiting_magnitude`'s NELM
  table), otherwise `None`.
- `target_priority_score`: combines altitude, framing score, and reach
  into the actual ranking key `planning.rank_targets` sorts by —
  multiplicative (`altitude/90 × fit × reach`), so a poor fit or a
  too-diffuse target for the site's sky vetoes/downgrades regardless of
  how high it sits, rather than needing tunable weights alongside
  altitude. Reduces to plain altitude for the common case
  (`fit == reach == 1.0`); `reach` defaults to 1.0 for any caller not yet
  passing one.
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

- Deep-sky catalog: 185 curated objects (63 Messier, 122 non-Messier —
  well-known astrophotography targets cataloged under NGC, IC, or another
  designation entirely, e.g. North America Nebula, Veil Nebula, Helix
  Nebula, Antennae Galaxies, the Medusa Nebula as Abell 21, Wolf's Cave
  Nebula as vdB 152, the Cave Nebula as Caldwell 9).
- Sourced against [OpenNGC](https://github.com/mattiaverga/OpenNGC)
  (CC-BY-SA-4.0) rather than memory alone once objects got obscure enough
  that misremembering a magnitude was a real risk. Two further expansion
  passes cross-referenced every target listed in Ruben Kier's *The 100 Best
  Astrophotography Targets* (chapters 1–12) and, later, Charles Bracken's
  *The Astrophotography Planner* (2nd ed.) table of contents against the
  catalog and added the ones missing; `catalog_id` is not restricted to
  Messier/NGC/IC — a number of the added targets only exist in the
  Sharpless, Abell, van den Bergh, or Caldwell catalogs and were sourced
  from SIMBAD/Wikipedia instead of OpenNGC once it had nothing for them.
  A number of both books' targets are left out because no reliably sourced
  magnitude exists for the object itself, distinct from a companion object
  or illuminating star it's routinely conflated with — e.g. the Angel
  Nebula (NGC 2170), the Tadpole Nebula (IC 410, OpenNGC/NED treat it as a
  duplicate of its embedded cluster NGC 1893), the Blue Horsehead Nebula
  (IC 4592, whose only published "magnitude" is its illuminating star Nu
  Scorpii's), and IC 417/IC 59 (no magnitude in OpenNGC, SIMBAD, or
  Wikipedia at all). Pure-Sharpless emission nebulae and Barnard/Lynds dark
  nebulae almost never carry a published integrated magnitude in either
  OpenNGC or SIMBAD (confirmed target-by-target, not assumed) — CTB1,
  Simeis 147, Barnard's Loop, the Tulip/Flying Bat/Lion/Lobster Claw/
  Scarlet Letter/Dolphin/Propeller/Gamma Cygni nebulae, the Snake/Pipe/
  Barnard's E/Dark Shark dark nebulae, and the Squid Nebula (OU4, no formal
  catalog designation at all) are left out on that basis.
- A third expansion pass cross-referenced Charles Bracken's *The
  Astrophotography Sky Atlas* Object Index (pp. 90–140, OCR'd via Claude
  Haiku from page scans) — 1,683 real object rows once "(see X)"
  cross-references are excluded, far broader than Kier's or the *Planner*'s
  curated lists since it's a full plate-atlas index, not a "best of."
  The atlas marks its own "highlight" objects in bold on the page, but the
  OCR pass preserved that bold formatting for only 2 of the 1,683 rows (a
  spot-check against unmistakable highlights like M31 and the Horsehead
  Nebula confirmed the signal was lost, not that they weren't highlighted)
  — so bold couldn't be used as a curation filter from the transcript, and
  won't be unless a fresh OCR pass explicitly preserves it. In its absence,
  candidates were filtered to rows with dec ≥ −30°, a Bracken editorial
  comment (his prose is selective — a proxy for "worth a note", present on
  only ~9% of rows), and object types outside the already-established
  no-magnitude categories (dark nebulae, galaxy groups/clusters, Abell
  planetary nebulae), narrowing 1,683 rows to 72 candidates, each then
  checked against a local pull of OpenNGC's `NGC.csv` + `addendum.csv` (and
  SIMBAD for the handful OpenNGC didn't cover). One filtering bug surfaced
  along the way: matching only against existing `catalog_id`/`aliases`
  missed that the Rosette Nebula and Little Gem Nebula were already in the
  catalog under different designations than the atlas uses (NGC 2237/2244
  vs. the atlas's NGC 2238; both already-present) — caught by also matching
  against existing `name` fields before finalizing, otherwise both would
  have been added as duplicate physical objects. 35 objects survived to be
  added: 8 fill genuine gaps in Messier coverage (M39, M49, M58, M59, M60,
  M61, M71, M73 — M73 is kept as `types: ["open_cluster"]` for lack of a
  better bucket even though it's named "Asterism M73" here, since modern
  data shows it's just four unrelated stars, not a real cluster), the rest
  are non-Messier well-known targets the catalog was missing outright —
  Mirach's Ghost (NGC 404), the UFO Galaxy (NGC 2683), the 37 Cluster (NGC
  2169), the Robin's Egg Nebula (NGC 1360), both Andromeda dwarf-spheroidal
  companions (NGC 147, NGC 185), and 21 further galaxies/nebulae/clusters
  in the mag 7–13.2 range. A live OCR bug turned up mid-pass and is worth
  naming: the atlas's own comment column had at least one row-shift, where
  NGC 147's comment ("Faint dwarf spheroidal galaxy" — correct, NGC 147 is
  one) had shifted up onto the NGC 146 row (an open cluster, for which that
  comment makes no sense) — caught by cross-checking comment text against
  OpenNGC's own object type before trusting it, not by the comment-presence
  filter itself, which had already dropped NGC 147 as a false negative from
  the shift; both ended up added on their own (correct) merits regardless.
  Of the 37 initially-plausible candidates that made it to OpenNGC/SIMBAD
  lookup, 2 turned out to already be in the catalog (above) and 35 were
  new; the remaining candidates and the reasons they were skipped are in
  [SKIPPED-OBJECTS.md](./SKIPPED-OBJECTS.md) —
  new cases beyond the already-documented star/nebula-magnitude-conflation
  and Sharpless/Abell/Barnard patterns: NGC 6820's B-Mag=15 describes a
  0.5′ knot inside the 30′ nebula Sh2-86 actually is, not the nebula itself
  (same conflation shape as the star cases, just with a sub-feature instead
  of a star); OpenNGC/NED flag both IC 4606 ("Antares Nebula") and IC 1316
  as "nothing here, nominal position" — the designations themselves don't
  reliably resolve to the pictured object; and NED's note on NGC 1555
  ("Hind's Variable Nebula") cites Strauss et al. 1992 identifying the
  position as a star, not a confirmed extant nebula, which is a step
  further than an unreliable magnitude — the object's own physical reality
  is in dispute; NGC 6874 had the same flavor of problem one level down —
  OpenNGC types it a stellar association (no photometric magnitude at all)
  rather than the open cluster Bracken lists it as, tangled up in the same
  NGC 6874/6882/6885 duplicate-designation confusion NED flags as "not
  certain" for its neighbors — though a 2026-09-20 recheck found its
  position/size were real after all and added it anyway (see this
  section's own note on `mag_unknown.yaml` Block 12, below, and
  SKIPPED-OBJECTS.md).
- With all three books' skip lists combined (see
  [SKIPPED-OBJECTS.md](./SKIPPED-OBJECTS.md) for the full, per-object list),
  the accumulated exclusions are overwhelmingly structural
  rather than a temporary research gap: diffuse emission nebulae, dark
  nebulae, and Abell planetary nebulae essentially never get a published
  per-object integrated magnitude at all — that's a fact about what gets
  photometered, not a gap more searching closes. The exceptions worth an
  actual future revisit are the small "designation itself is disputed"
  set — IC 4606, IC 1316, NGC 1555, and Simeis 147 (NGC 6874 resolved,
  see above) — where a future SIMBAD/NED correction, not a deeper search,
  is what could change the answer.
- Magnitudes prefer OpenNGC's B-Mag field over V-Mag (an early extraction
  pass that preferred V-Mag whenever present produced silently wrong
  values, e.g. the Sculptor Galaxy's V-Mag=11.11 vs. its correct
  B-Mag≈7.9; fixed with a "prefer B, fall back to V" rule with an anomaly
  guard).
- Curation stops at objects with a real common name and a source that
  vouches for their magnitude — reaching down to ~mag 16 now that
  non-OpenNGC sources are in play (the Medusa Nebula, mag 15.99, is the
  faintest entry); going deeper still would mean pulling in anonymous,
  rarely imaged objects mostly known by catalog number alone, which
  stretches "well-known target" past what a name-only human curation pass
  can vouch for.
- Every entry also carries `types` (see `engine/models.py` above), sourced
  the same evidentiary way as magnitude — SIMBAD's own object-type field
  per `catalog_id`/alias, not assumed from the common name (e.g. IC 2574
  "Coddington's Nebula" is, per SIMBAD, actually a galaxy, not a nebula at
  all; NGC 7380 "Wizard Nebula" is SIMBAD's open cluster NGC 7380 plus the
  surrounding emission nebula the popular name actually refers to). A
  `galaxy_group` tag is added only where this catalog's own entry already
  names the object as part of one (Leo/Draco Trios, Stephan's Quintet,
  Hickson 44, Antennae Galaxies, Deer Lick Group, Markarian's Chain members
  M84/M86, the Andromeda companions, etc.) — not researched for every plain
  galaxy that happens to have neighbors.
- Split into `mag_*.yaml` files by apparent magnitude, not by source
  catalog — a bin file doesn't care whether an object is Messier, NGC, or
  IC, and a site+rig's computed limiting magnitude will eventually be able
  to load only the bins it needs. One exception: `mag_unknown.yaml` (empty
  for now) holds objects with no reliably sourced integrated magnitude at
  all — admission there still requires a real `catalog_id` and
  `size_arcmin`, just not a magnitude. A dedicated policy test
  (`test_only_the_unknown_bin_file_omits_magnitude`) keeps "no magnitude"
  from silently landing in the wrong file.
- Every physical object gets exactly one `Target` entry regardless of how
  many catalogs list it — `Target.aliases` carries the others (e.g. M31's
  `aliases=("NGC 224",)`; M16's Eagle Nebula carries both `NGC 6611` and
  `IC 4703`, its two other designations), so the same object can never show
  up twice under two different names.
- Two policy tests keep every entry within scope: declination ≥ −30°
  (reaches ≥20° altitude from any "40°N or further north" site — M83 at
  −29.87° is the existing edge case that pins this boundary) and, for
  entries with a known magnitude, ≤ 18.6 (this project's widest aperture,
  Redcat 51, under its darkest sky in scope, Bortle 2) — the catalog is
  well within that ceiling today, so there's room to go deeper later
  without hitting it. `mag_unknown.yaml` entries are exempt from the
  magnitude ceiling — there's nothing to check it against.
- LBN 550, LBN 552, and LBN 555 (`mag_unknown.yaml`, Block 11) were added
  to cover ROADMAP.md's own multi-object-grouping example — three faint
  patches of Cepheus's Integrated Flux Nebula, routinely imaged together.
  Coordinates/sizes from VizieR's Lynds' Catalogue of Bright Nebulae (CDS
  VII/9); cross-checked against SIMBAD, which confirmed each position and
  the absence of a magnitude for all three. The roadmap text's other
  example pairing, "NGC 2244 + 2624", turned out not to check out: NGC
  2624 is a real object, but an unrelated mag-14.5 barred spiral galaxy in
  Cancer, nowhere near the Rosette Nebula's NGC 2244 — almost certainly a
  transposed-digit typo for NGC 2264 (the Christmas Tree Cluster, already
  in this catalog and already grouping with NGC 2261 in practice). Left
  un-added rather than adding the wrong NGC 2624 to force the example.
- NGC 6874 (`mag_unknown.yaml`, Block 12) was added on a 2026-09-20
  recheck of SKIPPED-OBJECTS.md, prompted by user-supplied German
  Wikipedia/OpenNGC/NED links — it turned out to have a real, citable
  position and size after all (previously miscategorized alongside IC
  1316 as "no position/data at all"), just no sourced magnitude and an
  ambiguous type (OpenNGC: stellar association; SIMBAD: unknown nature;
  Wikipedia/Bracken: open cluster) — `types: ["open_cluster"]` follows
  the M73 "lack of a better bucket" precedent. IC 1316 itself was
  reconfirmed as genuinely absent (OpenNGC's own NED-notes field: "nothing
  here, nominal position") — still correctly excluded. Two more
  SKIPPED-OBJECTS.md items (OU4/Squid Nebula, IC 1318b) got cross-
  referenced directly as comments on their host entries (Sh2-129, IC
  1318) in the same pass, rather than added as separate entries — neither
  has a citable magnitude or a formal catalog designation of its own.

## `nachtlotse/planning.py`

- Sits between the pure `engine` core and any UI: `plan_night(site, rig,
  when)` runs the whole pipeline — dark window, moon illumination, ranked
  targets (`rank_targets`, rig-aware field-rotation gating included),
  weather (`fetch_weather_summary`, optional and network-only here), and a
  `shortlist` of the top `SHORTLIST_SIZE` ranked targets, each with its own
  `verdict_for_target` call — into one `NightPlan`. There is no single hero
  target or single verdict for the night; two shortlisted targets at
  different altitudes can land on different GO/MARGINAL/SKIP levels.
  Kept separate from `cli.py` (the current front end) so a future one
  reuses the same pipeline instead of duplicating it — this is exactly
  what happened with the now-retired Streamlit UI, which called the same
  `plan_night()` cli.py does.
- Not UI code itself — no printing, no framework imports — which is what
  keeps it shared instead of becoming a second implementation.
- `rank_targets`/`plan_night` take a `limit` param (`DEFAULT_MAX_EVALUATED
  = 50`) capping how many catalog targets are *evaluated* (not returned) —
  the first N matching any `--type` filter, in catalog order
  (magnitude-binned, brightest first), skipped before the expensive
  ephemeris check. `limit=0` evaluates the full catalog (~400+ objects,
  ~30s); `None` falls back to the 50 default. Added because the unbounded
  per-run scan had become slow enough to make iterative development
  tedious — this was the roadmap's "object count limit" item, now closed.
- Multi-object grouping (the roadmap item of the same name, now closed):
  `rank_targets` clusters its own output via `engine.grouping.find_groups`
  (co-visible = every pairwise separation within `rig`'s field of view)
  and, for every cluster that's also *simultaneously* observable tonight
  (`_group_best_time` — angular closeness alone doesn't guarantee a
  shared moment; e.g. one member horizon-blocked while another peaks),
  folds the cluster into one `RankedGroup` — worst-member altitude/reach,
  the group's own fill-fraction fit — replacing the members' individual
  `RankedTarget` entries (`_fold_in_groups`). `RankedEntry =
  RankedTarget | RankedGroup` is what `NightPlan.ranked`/`.shortlist`
  actually carry now.
- Best-rig chooser (the roadmap item of the same name, now closed):
  `rank_targets_for_best_rig(site, rigs, when, ...)` /
  `plan_night_for_best_rig(...)` are `rank_targets`/`plan_night`'s
  multi-rig counterparts — for each target, every rig in `rigs` is
  scored and only the best-scoring one
  (`framing.target_priority_score`) is kept, carried as a `rig` field on
  each `RankedTargetForBestRig`/`NightPlanForBestRig` row instead of one
  rig for the whole plan. Deliberately does *not* run multi-object
  grouping: a co-visible group needs one shared field of view, but two
  targets here can each win with a different rig — see ROADMAP.md's
  "grouping-aware best-rig chooser" idea for the natural follow-up.

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
- `load_rigs()` (mirroring the existing `load_sites()`) returns every
  configured `Rig`, plain — used by `--best-rig`, which needs the whole
  list rather than one resolved-by-name record.
- `ProseConfig`/`load_prose_config()`: `--prose`'s own local config
  (Anthropic API key, chosen model), loaded the same local+template way
  as sites/rigs (`prose_local.yaml`/`prose_local.template.yaml`) but
  genuinely optional even when the file is missing — `load_prose_config()`
  returns None rather than the `require_sites`/`require_rigs` pattern of
  raising, since no command needs this to run. See `prose.py` below for
  how the key/model actually get resolved from it.

## `nachtlotse/weather/open_meteo.py`

- The one module allowed to touch the network: a free, no-key Open-Meteo
  client (clouds, wind, humidity, dew point) for a site's dark window.
- Optional by design — any failure (offline, bad response) raises
  `WeatherUnavailable`, which the CLI turns into "Weather: unavailable"
  rather than a crash; the ranking keeps working from sky geometry alone.

## `nachtlotse/prose.py`

- The LLM-prose roadmap item, now closed: the one module allowed to call
  the Claude API (`anthropic`, a new optional extra — `uv sync --extra
  prose`), and — unlike weather — never called unless `lotse plan
  --prose` explicitly asks for it. `generate_nightly_briefing(plan)`
  phrases `plan`'s already-decided facts (`build_briefing_facts`, built
  straight from `NightPlan`/`NightPlanForBestRig`'s own fields, not from
  `cli.py`'s print formatting) as a short prose briefing — a strict
  system prompt forbids the model from stating any number, time, or
  verdict beyond what's given, per CLAUDE.md's Guiding principle.
- Deliberately fails loudly, not softly: `ProseUnavailable` (package not
  installed, no API key configured, or the request itself failed)
  propagates out to the CLI rather than degrading to "no briefing this
  time" the way a missing weather forecast does — since the call only
  ever happens because the user explicitly asked for it, silently
  omitting the result would hide that they didn't get what they asked
  for.
- `_import_anthropic()`/`_request_briefing_text()` are the lazy-import
  and API-call seams (mirroring `chart_export._import_matplotlib()`),
  so the test suite exercises every failure path — and a scripted
  "happy path" response — without the `anthropic` package installed or
  any real network access.
- The API key and model both resolve through `data/store.load_prose_config()`
  first — `prose_local.yaml` (gitignored, `prose_local.template.yaml`
  alongside it, same pattern as sites/rigs but entirely optional, per
  `store.py`'s own docstring) — falling back to the `ANTHROPIC_API_KEY`
  environment variable (key only) and `DEFAULT_MODEL` (model only) when
  that file doesn't set them. `resolve_model()` is public so `cli.py`
  can print which model actually ran, not just the constant default.

## `nachtlotse/engine/scoring.py`

- The GO/MARGINAL/SKIP verdict for a single target: pure and deterministic
  given an altitude plus an optional `WeatherSummary`, so it never touches
  the network itself. `planning.plan_night` calls it once per shortlisted
  target, not once for the night as a whole.
- Cloud cover, wind, dew-point margin, and low altitude can each downgrade
  the verdict, worst-wins; thresholds are named module constants, called
  out as a tunable heuristic rather than physics (per CLAUDE.md's M4 note).
- A missing forecast (`weather=None`) also caps the verdict at MARGINAL —
  GO always means "cloud/wind/dew forecast checked and clear", never "sky
  geometry looked fine and we couldn't check the rest".

## `nachtlotse/cli.py`

- `lotse plan [--site NAME] [--rig NAME] [--date YYYY-MM-DD] [--limit N]`
  calls `planning.plan_night` and prints the result: dark window, moon
  illumination, weather summary, a numbered shortlist with its own
  GO/MARGINAL/SKIP verdict per target, and the full ranked table with
  framing-fit and surface-brightness-reach columns; `lotse sites` /
  `lotse rigs` list what's configured.
- `--limit N` caps evaluated catalog objects (default: 50); `--limit 0`
  evaluates every catalog object. See `planning.py` above for what
  "evaluated" means and why the cap exists.
- The ranked list is sorted by `framing.target_priority_score` (altitude ×
  framing fit × reach, descending) — the "Max Alt" column alone no longer
  decides the order. A target whose best window is horizon- or
  rotation-limited can already rank below one with a lower transit but a
  cleaner shot; a target that barely fits the frame (e.g. a small
  planetary nebula on a wide-field rig), or is too diffuse for the site's
  sky darkness (e.g. a large faint nebula from a bright site), is now
  deprioritized the same way, instead of winning hero status purely for
  sitting high in the sky.
- `--chart [PATH]`: writes the shortlist's alt/az polar overview as a PNG
  (`chart_export.save_shortlist_chart`) — `nargs="?"` so the bare flag
  writes to `chart_export.DEFAULT_CHART_FILENAME` in the current
  directory (overwriting any existing file there) and a value picks a
  different path. Lazily imports matplotlib (`uv sync --extra charts`) so
  plain `lotse plan` never needs it; a missing install turns into an
  actionable stderr message and exit code 2, not a traceback.
- A `RankedGroup` entry (see `planning.py` above) renders as one row/
  shortlist line: member names joined with " + " (`_entry_label`) and
  every distinct member category in the "Type" column (`_entry_types`) —
  one verdict for the whole group, not one per member.
- `--best-rig`: the best-rig chooser, `_cmd_plan_best_rig`'s own
  rendering path (`planning.plan_night_for_best_rig` — see `planning.py`
  above). Mutually exclusive with both `--rig` (there's no longer one
  rig to name) and `--chart` (not wired up yet); the ranked table gets
  an extra "Rig" column, the shortlist labels each entry with its
  winning rig in parentheses.
- `--prose`: prints an LLM-written nightly briefing after everything
  else (`planning.py`'s numbers/verdicts print first regardless — prose
  only ever supplements them, never replaces them), via
  `prose.generate_nightly_briefing` (see `prose.py` above). Works with
  `--best-rig` too. Only attempted when the shortlist is non-empty —
  nothing to brief about otherwise; `prose.ProseUnavailable` turns into
  an actionable stderr message and exit code 2, the same contract
  `--chart` uses for a missing extra.

## `nachtlotse/charting.py` and `nachtlotse/chart_export.py`

- `charting.py`: pure alt/az → (x, y) polar-projection geometry — zenith
  at the center, the true horizon at the rim, azimuth clockwise from north
  at the top. No charting-library dependency of its own (not even
  matplotlib), so it's just as usable from a future UI as from the CLI.
  Produces `Track` (a shortlisted target's path, split into segments so an
  object that dips below the horizon mid-window doesn't get its two
  above-horizon arcs joined through the ground), the horizon-blocked wedge
  polygon straight from `HorizonProfile.min_alt(az)`, grid-ring points, and
  a validated CVD-safe categorical palette (`SHORTLIST_PALETTE`, 5 slots —
  matches `planning.SHORTLIST_SIZE`).
- `chart_export.py`: the CLI's actual PNG renderer, built on matplotlib
  (`Agg` backend, no display needed) — lazily imported behind
  `_import_matplotlib()` so tests can force the "not installed" path
  without needing to actually uninstall it.
- This split exists because a Streamlit UI once rendered the same overview
  in Altair — `charting.py` is what stayed reusable once that UI was
  retired (see CLAUDE.md's M5 note); the projection math and horizon-wedge
  geometry never had to be duplicated for `chart_export.py`.

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
- `charting.py`'s geometry is tested without any charting library at all
  (known projection points, ring/wedge shapes, segment-splitting on a
  monkeypatched altitude series) — `chart_export.py`'s PNG rendering skips
  itself (`pytest.importorskip("matplotlib")`) when the `charts` extra
  isn't installed, but its "matplotlib missing" error path is tested
  unconditionally by forcing the `_import_matplotlib` seam to raise.

## Not yet implemented (by design)

The MVP (M0–M5) is complete. Ideas kept for later — a "best rig for this
target" chooser, current-events alerts, a native macOS app, and more —
are listed in [ROADMAP.md](./ROADMAP.md), not scheduled to any milestone.

## MVP roadmap (milestones, detail)

Moved here from CLAUDE.md, which now only summarizes that the MVP is
complete — this is the milestone-by-milestone scope and DoD, kept for
reference. Follow-on work is tracked in [ROADMAP.md](./ROADMAP.md)
instead of new milestones.

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
  long-term goal (Python, not Swift — see [ROADMAP.md](./ROADMAP.md)), that
  double maintenance wasn't worth it, so the Streamlit UI was removed and
  the CLI is the only front end again.

The MVP (M0–M5) is complete.

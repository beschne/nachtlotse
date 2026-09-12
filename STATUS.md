# Status

Detailed implementation status, module by module. For the milestone overview
and roadmap, see [README.md](./README.md) and [CLAUDE.md](./CLAUDE.md).

- ✅ **M0 — Scaffolding & engine core**, done.
- ✅ **M1 — Moon & dark window**, done.
- ✅ **M2 — Horizon profiles & multiple sites**, done.
- ✅ **M3 — Rig scoring, framing & field rotation**, done.
- ✅ **M4 — Weather & verdict**, done.

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
  the Quickstart in README.md). `mount.kind` is a setup choice, not a fixed
  hardware property — even an alt-az smart telescope can be wedge-mounted
  and polar-aligned for true eq tracking, so the same optics/sensor can
  appear as two separate rig entries under different aliases (e.g. `S30P`
  for a Seestar's native alt-az ball mount vs. `S30P-EQ` on a latitude
  wedge); pick per session with `--rig`.
- `nachtlotse/weather/open_meteo.py` — the one module allowed to touch the
  network: a free, no-key Open-Meteo client (clouds, wind, humidity, dew
  point) for a site's dark window. Optional by design — any failure
  (offline, bad response) raises `WeatherUnavailable`, which the CLI turns
  into "Weather: unavailable" rather than a crash; the ranking keeps
  working from sky geometry alone.
- `nachtlotse/engine/scoring.py` — the GO/MARGINAL/SKIP verdict for the
  hero (top-ranked) target: pure and deterministic given an altitude plus
  an optional `WeatherSummary`, so it never touches the network itself.
  Cloud cover, wind, dew-point margin, and low altitude can each downgrade
  the verdict, worst-wins; thresholds are named module constants, called
  out as a tunable heuristic rather than physics (per CLAUDE.md's M4 note).
- `nachtlotse/cli.py` — `lotse plan [--site NAME] [--rig NAME] [--date YYYY-MM-DD]`
  ranks tonight's (or the given date's) *observable* targets (night + moon
  + altitude + horizon + rig-aware field rotation) by best altitude within
  the dark window, with a framing-fit column, a weather summary, and a
  GO/MARGINAL/SKIP verdict for the top target; `lotse sites` / `lotse rigs`
  list what's configured. The list is sorted descending by "Max Alt" — the
  highest altitude each target safely reaches under *all* active
  constraints, not necessarily its true meridian-transit altitude, so a
  target whose best window is horizon- or rotation-limited can rank below
  one with a lower transit but a cleaner shot.
- Tests against independently known astronomical/textbook values (Polaris
  altitude ≈ geographic latitude, transit altitude = 90° − lat + dec, a target
  coincident with the Moon's own position always fails separation, a
  full-circle horizon wall drops an otherwise-observable target, plate scale
  = 206.265 × pixel_um / focal_length_mm, field-rotation rate calibrated
  numerically against astroplan's own parallactic angle near vs. far from
  the zenith) plus catalog/store/CLI smoke tests — including that the same
  sky yields different target lists at two sites with different horizons,
  a near-zenith target is downgraded for an alt-az rig but not an eq one,
  overcast sky yields SKIP with the cloud cover named as the reason, and a
  clear window with a low target yields MARGINAL. The weather client's own
  tests mock `urllib.request.urlopen` — like the rest of the suite, they
  never touch the real network.

## Not yet implemented (by design)

A "best rig for this target" chooser — `lotse plan` scores targets for
whichever rig you pass, it doesn't yet pick between rigs. Later milestones
(M5 UI, M6 comfort/prose) are documented in [CLAUDE.md](./CLAUDE.md).

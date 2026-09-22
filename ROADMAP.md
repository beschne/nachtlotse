# Roadmap

The MVP (M0–M5) is complete and history — see
[STATUS.md](./STATUS.md#mvp-roadmap-milestones-detail) for that
milestone-by-milestone breakdown. This file tracks what comes after it.
For the guiding principle, architecture, and coding conventions the items
below must still follow, see [CLAUDE.md](./CLAUDE.md).

## Ideas for after the MVP, in priority order

1. **Framing preview for selected targets:** render what a target would
   actually look like through the given rig — its angular size/shape
   against the rig's field of view (from `framing.py`'s FoV/fill-fraction
   math) — rather than only the numeric `framing_score`/reach. A visual
   check for "does this actually fit, and how tightly" for a target picked
   off the shortlist, complementing (not replacing) the existing polar
   `--chart`, which shows where in the sky, not how it frames. To be implemented
   for the CLI and the GUI. Both on demand only and cached.
2. **Current events:** well-placed comets, supernova alerts; later also minor
   planets/asteroids and near-Earth objects (NEOs).
3. **Session log:** record what's already been captured, and when — total
   exposure time per target, logged per session. Prior exposure on a target
   is informational, not a deterrent; it doesn't mean the target drops out of
   contention, more can still be worth shooting. No attached photos. 

## Non-prioritized ideas

Worth doing eventually, but not ranked against the list above — pick one
up when it fits, not in any particular order.

- **Multilingual UI/CLI text** (at minimum German and English). Everything
  user-facing is English-only for now; this stays parked until there's a
  reason to localize.
- **Catalog object cross-references + descriptions:** a sub-feature or
  companion object embedded within another catalog entry (the Squid
  Nebula/OU4 inside Sh2-129, IC 1318b inside IC 1318, the NGC 6820 knot
  inside Sh2-86 — see SKIPPED-OBJECTS.md and the `mag_unknown.yaml`
  comments) can today only be documented as a source comment in the YAML
  — invisible to `lotse plan`'s own output. A `references`/`related`
  field (pointing at another entry's `catalog_id`) plus a free-text
  `description` field on `Target` would let that surface for real (e.g.
  "M42 also contains the Running Man Nebula, NGC 1977") instead of living
  only in a comment nobody but the catalog's own maintainer ever reads.
  Most useful for objects-within-objects, but `description` alone would
  also give every entry a place for the kind of context this catalog's
  comments already accumulate — why a size/magnitude was chosen, what
  makes a target worth shooting — without needing to open the YAML source.
- **Grouping-aware best-rig chooser:** the best-rig chooser
  (`lotse plan --best-rig`) picks a winning rig per target independently,
  so it doesn't run multi-object grouping (`engine.grouping`) — two
  targets can each win with a *different* rig, leaving no single shared
  field of view to group against. Picking a best rig per target first,
  then finding the best co-visible grouping among whatever wins, would
  close that gap; not attempted in the first version (see
  `planning.rank_targets_for_best_rig`'s own docstring).
- **Sky chart: show all ranked, not just the shortlist.** The chart only
  plots `plan.shortlist` (5 entries) by default — a toggle to plot the
  full `plan.ranked` list instead (or as well) would show what's just
  outside the shortlist cutoff.
- **Sky chart PNG export: match the GUI canvas, Moon included.** The
  Sky chart tab's "Export PNG…" (see "Export from the GUI" above)
  reuses `chart_export.save_shortlist_chart` — the same render
  `lotse plan --chart` produces, chart and legend baked into one
  matplotlib figure so they land in the same PNG. But that render
  doesn't match what the tab itself is showing: `chart_export.py`
  never draws the Moon (track or phase icon, both real
  `engine.ephemeris` output already reused elsewhere — `charting.
  moon_track`, `gui/sky_chart.py`'s `_moon_phase_path` — just not
  wired into this module), colors each track by a rotating palette
  index rather than by verdict (`gui/sky_chart.py`'s
  `_verdict_line_color`), and doesn't star-mark favorites the way
  `LegendPanel._legend_row` does on screen. Closing the gap means
  teaching `chart_export.py` to draw all three, not switching the
  export to a `QWidget.grab()` of the live canvas (that would drop
  the legend, which lives in a separate card/widget — see the "not
  trivial" note on the Export item above).
- **In-app sites/rigs editor:** the Sites/Rigs screens are read-only —
  `sites_local.yaml`/`rigs_local.yaml` stay hand-edited for now. An
  editor that round-trips them without mangling existing comments/
  formatting is real, separate scope.
- **Catalog tab (GUI), with in-app favorite toggling:** a "Catalog" tab
  listing every catalog target — not just what's ranked/shortlisted
  tonight — sortable/filterable by type and magnitude. The concrete
  place to flip a target's `favorite` flag (see "Favorites in the
  catalog", done) from the GUI instead of hand-editing
  `favorites_local.yaml` directly, which still works today and stays the
  source of truth either way. Shares the same open problem as the in-app
  sites/rigs editor idea just above: writing back into YAML without
  mangling existing comments/formatting is real, separate scope.
- **EQ mount "danger zone" — counterweight-required region (rig
  "ZWO Seestar S30 Pro (EQ wedge)" / "S30P-EQ"):** unlike the alt-az
  field-rotation gate `framing.has_safe_field_rotation` already models,
  nothing accounts for EQ-mount mechanical strain yet. West of the
  meridian, this rig's worm/gear mesh loses tracking engagement at lower
  altitude — from ~5 logged sessions: above 55° stays safe; 50-55° is an
  untested "transition" band; 40-50° loses ~10-30% of tracking rate
  ("moderate"); at or below 40° loses over 30% ("severe"). East of the
  meridian is always safe. A counterweight only softens the effect,
  never removes it — ~6% residual error remained at 25° altitude even
  with a 195 g counterweight — so this should never collapse into a
  binary "counterweight fitted = safe" toggle.

  Caveats worth keeping as an explicit comment in any real
  implementation, not presented as settled fact: the thresholds are
  provisional (only ~5 sessions behind them, refinable later from a
  real session log); the high-west corner (above 55°, past transit) is
  untested, so "safe" there is assumed, not measured; and high northern
  declinations (circumpolar from this site, dec above 60°) never dip
  low enough to enter the zone at all — the altitude check already
  handles that automatically.

  Its only surfaced effect is meant to be visual, on the sky chart
  (`gui/sky_chart.py`): shade the danger-zone region red (severity-graded,
  deeper red for "severe"), the same way `_paint_horizon_wedge` already
  shades the horizon-blocked wedge — no separate text warning. Needs
  hour angle (from RA + local sidereal time, not currently exposed by
  `engine.ephemeris`) or an equivalent azimuth check (west sector,
  roughly 180-360° past transit).
- **Structured `lotse plan --json` output**, alongside the existing
  human-readable table (not replacing it) — for external tooling
  (scripts, NINA, a future integration) to consume instead of parsing
  text output. (The native GUI itself doesn't need this — it imports
  `planning` directly, Python-native, no serialization in between; this
  is for anything that *isn't* Python.) Straightforward:
  `NightPlan`/`ShortlistEntry`/`RankedTarget` are already plain
  dataclasses/NamedTuples, so this is a serializer in `cli.py`, not an
  engine change.
- **Export today's pick to a NINA-compatible format.**
- **Sort/filter Best Sky and the Sites tab by the machine's own current
  location**, not just a configured reference site — useful mainly when
  traveling. Tried a plain `pyobjc-framework-CoreLocation` script for
  this (same approach the screenshot tooling already uses for
  `pyobjc-framework-Quartz`); macOS silently denies it
  (`kCLErrorDenied`) and never even lists the requesting process in
  System Settings' Location Services pane, since that dialog/listing
  needs a proper code-signed `.app` bundle with an
  `NSLocationWhenInUseUsageDescription` in its `Info.plist` — a bare
  CLI script can't get there. Real support means either such a helper
  app, or just asking the user for coordinates/an address to geocode,
  each visit.

## Out of scope (deliberately excluded)
- Mount control / session automation
- Cloud sync
- Accounts
- Southern-sky curation
- Mobile apps

Deliberately excluded; not reconsidered above without a specific reason to.

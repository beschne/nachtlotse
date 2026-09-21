# Roadmap

The MVP (M0–M5) is complete and history — see
[STATUS.md](./STATUS.md#mvp-roadmap-milestones-detail) for that
milestone-by-milestone breakdown. This file tracks what comes after it.
For the guiding principle, architecture, and coding conventions the items
below must still follow, see [CLAUDE.md](./CLAUDE.md).

## Ideas for after the MVP, in priority order

1. **Export from the GUI:** Shortlist/All ranked as CSV, the sky chart as
   a PNG (reusing `chart_export.py`'s matplotlib path, or a direct
   `QWidget.grab()` of the canvas), the briefing as `.txt`, and Sites/Rigs
   as `.txt`.
2. **GUI evaluation limit:** `lotse gui` calls `planning.plan_night`
   without a `limit`, so it already inherits the same
   `DEFAULT_MAX_EVALUATED` (50) cap the CLI defaults to — but unlike the
   CLI's own `--limit` flag, there's no sidebar control to change it
   (evaluate more, fewer, or 0/unlimited).
3. **Session log:** record what's already been captured, and when — total
   exposure time per target, logged per session. Prior exposure on a target
   is informational, not a deterrent; it doesn't mean the target drops out of
   contention, more can still be worth shooting. No attached photos.
4. **Current events:** well-placed comets, supernova alerts; later also minor
   planets/asteroids and near-Earth objects (NEOs).
5. **Multilingual UI/CLI text** (at minimum German and English). Everything
   user-facing is English-only for now; this stays parked until there's a
   reason to localize.
6. **Framing preview for selected targets:** render what a target would
   actually look like through the given rig — its angular size/shape
   against the rig's field of view (from `framing.py`'s FoV/fill-fraction
   math) — rather than only the numeric `framing_score`/reach. A visual
   check for "does this actually fit, and how tightly" for a target picked
   off the shortlist, complementing (not replacing) the existing polar
   `--chart`, which shows where in the sky, not how it frames.

## Non-prioritized ideas

Worth doing eventually, but not ranked against the list above — pick one
up when it fits, not in any particular order.

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
- **"Best sky" in the GUI:** `best_sky.py`/`lotse best-sky` (cross-site
  forecast cloud-cover comparison) has no GUI surface yet — the GUI can
  only plan for whichever single site is picked in the sidebar, not
  answer "which of my configured sites has the clearest sky tonight."
- **In-app sites/rigs editor:** the Sites/Rigs screens are read-only —
  `sites_local.yaml`/`rigs_local.yaml` stay hand-edited for now. An
  editor that round-trips them without mangling existing comments/
  formatting is real, separate scope.
- **Catalog tab (GUI), with in-app favorite toggling:** a "Catalog" tab
  listing every catalog target — not just what's ranked/shortlisted
  tonight — sortable/filterable by type and magnitude. The concrete
  place to flip a target's `favorite` flag (see "Favorites in the
  catalog", done) from the GUI instead of hand-editing a `mag_*.yaml`
  file directly, which still works today and stays the source of truth
  either way. Shares the same open problem as the in-app sites/rigs
  editor idea just above: writing back into YAML without mangling
  existing comments/formatting is real, separate scope.
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

## Out of scope (deliberately excluded)
- Mount control / session automation
- Cloud sync
- Accounts
- Southern-sky curation
- Mobile apps

Deliberately excluded; not reconsidered above without a specific reason to.

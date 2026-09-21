# Roadmap

The MVP (M0–M5) is complete and history — see
[STATUS.md](./STATUS.md#mvp-roadmap-milestones-detail) for that
milestone-by-milestone breakdown. This file tracks what comes after it.
For the guiding principle, architecture, and coding conventions the items
below must still follow, see [CLAUDE.md](./CLAUDE.md).

## Ideas for after the MVP, in priority order

1. **Favorites in the catalog:** a starred/favorite flag on a target,
   independent of ranking — motivated by variable-star photometry (e.g.
   T Coronae Borealis, "T CrB") that should be measured and shown every
   session regardless of where it'd normally fall in the shortlist cutoff.
   Touches more than the GUI: the catalog/engine model needs the flag
   itself, `planning` needs to fold favorites into (or alongside) the
   shortlist rather than let them get crowded out, and the GUI needs
   somewhere to show them — a pinned section within Shortlist, or their
   own tab — plus the sky chart should plot favorite tracks even when
   they're not otherwise part of the top-ranked shortlist.
2. **Export from the GUI:** Shortlist/All ranked as CSV, the sky chart as
   a PNG (reusing `chart_export.py`'s matplotlib path, or a direct
   `QWidget.grab()` of the canvas), the briefing as `.txt`, and Sites/Rigs
   as `.txt`.
3. **Hourly cloud cover for the astro-night:** `weather/open_meteo.py`
   currently aggregates cloud cover over the whole dark window into one
   `WeatherSummary` (`max_cloud_cover_pct`/`avg_cloud_cover_pct`). Instead,
   surface the hour-by-hour Open-Meteo series, clipped to the astronomical
   dark window (`constraints.dark_window`) rather than the full calendar
   night, so a fully-clear window that closes early or a socked-in window
   that clears at 2am shows up as a shape, not one averaged number.
4. **GUI evaluation limit:** `lotse gui` calls `planning.plan_night`
   without a `limit`, so it already inherits the same
   `DEFAULT_MAX_EVALUATED` (50) cap the CLI defaults to — but unlike the
   CLI's own `--limit` flag, there's no sidebar control to change it
   (evaluate more, fewer, or 0/unlimited).
5. **Session log:** record what's already been captured, and when — total
   exposure time per target, logged per session. Prior exposure on a target
   is informational, not a deterrent; it doesn't mean the target drops out of
   contention, more can still be worth shooting. No attached photos.
6. **Current events:** well-placed comets, supernova alerts; later also minor
   planets/asteroids and near-Earth objects (NEOs).
7. **Multilingual UI/CLI text** (at minimum German and English). Everything
   user-facing is English-only for now; this stays parked until there's a
   reason to localize.
8. **Framing preview for selected targets:** render what a target would
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

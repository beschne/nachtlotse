# Roadmap

The MVP (M0–M5) is complete and history — see
[STATUS.md](./STATUS.md#mvp-roadmap-milestones-detail) for that
milestone-by-milestone breakdown. This file tracks what comes after it.
For the guiding principle, architecture, and coding conventions the items
below must still follow, see [CLAUDE.md](./CLAUDE.md).

## Ideas for after the MVP, in priority order

1. **Best-rig chooser:** `lotse plan` scores targets for whichever rig you pass,
   it doesn't yet pick between rigs. `framing_score`
   (`engine/framing.py`) now scales with fill fraction (1.0 at a fill
   fraction of 1.0, fading toward 0.0 as the target shrinks toward a speck
   or, past 1.0, as it clips) instead of the old flat 20%-100% plateau, so
   the gradient a chooser needs — preferring the more format-filling rig,
   not just any non-clipping one — is in place. The chooser itself (picking
   between rigs, not just scoring one) is still to build.
2. **LLM prose (nightly briefing)** via the Claude API — numbers strictly from
   the engine, never computed by the LLM. No longer optional; this is the
   presentation layer that wraps the engine's numbers in readable prose.
3. **Session log:** record what's already been captured, and when — total
   exposure time per target, logged per session. Prior exposure on a target
   is informational, not a deterrent; it doesn't mean the target drops out of
   contention, more can still be worth shooting. No attached photos.
4. **Current events:** well-placed comets, supernova alerts; later also minor
   planets/asteroids and near-Earth objects (NEOs).
5. **Framing preview for selected targets:** render what a target would
   actually look like through the given rig — its angular size/shape
   against the rig's field of view (from `framing.py`'s FoV/fill-fraction
   math) — rather than only the numeric `framing_score`/reach. A visual
   check for "does this actually fit, and how tightly" for a target picked
   off the shortlist, complementing (not replacing) the existing polar
   `--chart`, which shows where in the sky, not how it frames.

## Non-prioritized ideas

Worth doing eventually, but not ranked against the list above — pick one
up when it fits, not in any particular order.

- **Export today's pick to a NINA-compatible format.**
- **Multilingual UI/CLI text** (at minimum German and English). Everything
  user-facing is English-only for now; this stays parked until there's a
  reason to localize.
- **Structured `lotse plan --json` output**, alongside the existing
  human-readable table (not replacing it) — the interface a future native
  app, or any other tooling, consumes instead of parsing text output.
  Straightforward: `NightPlan`/`ShortlistEntry`/`RankedTarget` are already
  plain dataclasses/NamedTuples, so this is a serializer in `cli.py`, not
  an engine change.
- **Hourly cloud cover for the astro-night:** `weather/open_meteo.py`
  currently aggregates cloud cover over the whole dark window into one
  `WeatherSummary` (`max_cloud_cover_pct`/`avg_cloud_cover_pct`). Instead,
  surface the hour-by-hour Open-Meteo series, clipped to the astronomical
  dark window (`constraints.dark_window`) rather than the full calendar
  night, so a fully-clear window that closes early or a socked-in window
  that clears at 2am shows up as a shape, not one averaged number.
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
- **Native macOS app** — the long-term UI goal now that Nachtlotse's GitHub
  presence is explicitly a portfolio piece, not just a personal tool.
  Python throughout (Swift is deliberately out of scope); exact toolkit
  undecided (PySide6/Qt is the leading candidate) — to be designed once
  the CLI's own feature set (the prioritized list above) has matured
  further. Whatever it consumes — `--json` output, or the engine/`planning`
  layer directly if it's Python-native — the same `cli.py` →
  `engine`/`data` dependency direction applies; see the Streamlit MVP's
  retirement (M5, in [STATUS.md](./STATUS.md#mvp-roadmap-milestones-detail))
  for why this project doesn't maintain two front ends at once.

## Out of scope (deliberately excluded)
- Mount control / session automation
- Cloud sync
- Accounts
- Southern-sky curation
- Mobile apps

Deliberately excluded; not reconsidered above without a specific reason to.

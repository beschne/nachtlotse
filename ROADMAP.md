# Roadmap

The MVP (M0–M5) is complete and history — see
[STATUS.md](./STATUS.md#mvp-roadmap-milestones-detail) for that
milestone-by-milestone breakdown. This file tracks what comes after it.
For the guiding principle, architecture, and coding conventions the items
below must still follow, see [CLAUDE.md](./CLAUDE.md).

## Ideas for after the MVP, in priority order

1. **Export to SkySafari (`.skylist`):** write the shortlist, the full
   ranking, or tonight's current events as a SkySafari observing list, so
   the night's targets open directly in SkySafari on the phone or tablet at
   the telescope. From the CLI (e.g. `lotse plan --skylist PATH`) and as an
   Export button in the GUI, next to CSV. Catalog objects can go by
   designation; comets, supernovae and novae may need their coordinates or a
   name SkySafari itself knows. Build the format from a list exported by
   SkySafari, not from memory.
2. **Current events:** comets (3.3.0) and supernovae/novae (3.4.0) are
   done — see STATUS.md. Still open:
   - **Galactic novae's current brightness:** TNS lists them, but only
     with their discovery magnitude; AAVSO photometry could say how bright
     one is now. The same would cover watching a recurrent nova already in
     the catalog (T CrB) for an outburst, which TNS wouldn't necessarily
     list.
   - **TNS bot credentials (optional):** requests could identify as a bot
     (courtesy, higher limits than anonymous search's 10 a minute), and
     TNS photometry could become a second brightness source.
   - **Minor planets/asteroids and near-Earth objects (NEOs):** fast
     movers that would need real motion tracking, not the per-night
     snapshot comets get.
3. **Session log:** record what's already been captured, and when — total
   exposure time per target, logged per session. Prior exposure on a target
   is informational, not a deterrent; it doesn't mean the target drops out of
   contention, more can still be worth shooting. No attached photos. 

## Think about

Candidate ideas not yet slotted into the prioritized list above — surfaced
while scanning comparable tools for gaps, not committed to, and some in
tension with the engine's own scope (open catalog, not curation) or its
offline-first design. Listed in priority order.

1. **Night verdict above the per-target verdicts:** one line at the top
   of `lotse plan` and the GUI answering "is it worth setting up
   tonight?" before "what do I shoot?" — e.g. "GO, clear 21:30–03:10
   (5.7 h)" or "SKIP: longest clear run 1 h from 22:00, rule needs 3 h",
   plus a "held back by" line naming the terms that cost the most
   (Moon, cloud, dew, wind). The per-target GO/MARGINAL/SKIP stays; this
   frames it. Needs 2.
2. **Hourly weather instead of a window aggregate:** `weather/open_meteo.py`
   already fetches hourly values, but `summarize_window` collapses them
   into `WeatherSummary`'s max/avg — an average of 40% cloud can mean
   "clear until 01:00, then closed". A pure engine function that finds
   contiguous clear runs inside the dark window (configurable minimum
   hours and cloud threshold), with high thin cloud counted at half
   weight (Open-Meteo has `cloud_cover_low/mid/high`), and per target:
   does its best time fall in the clear part of the night?
3. **Per-target difficulty rating:** an `Easy`/`Moderate`/`Hard`/`Elite`
   field on `Target`, derived from apparent size, magnitude, and
   circumpolar-vs-seasonal accessibility. Shown in CLI output, GUI, and
   chart labels. Complements the GO/MARGINAL/SKIP verdict rather than
   replacing it — the verdict says "is this shootable tonight", difficulty
   says "how hard is it to get right".
4. **Integration time estimation:** a minimum-exposure estimate per target
   from magnitude, sensor pixel size, and mount tracking, shown alongside
   the verdict. Answers "how long does this take" — the natural follow-up
   once a target clears GO.
5. **Per-target reference images:** lightweight thumbnail paths in the
   catalog YAML (CC-licensed), shown in the GUI and optionally on the
   polar chart, so a target on the shortlist isn't just a name and a
   score.
6. **Lunar-aware object-type weighting:** boost narrowband-friendly types
   (emission nebulae) in scoring as moon phase rises above ~0.5, and
   broadband types (galaxies, reflection nebulae) as it drops below
   ~0.3. `engine.ephemeris.moon_phase_angle_deg` already exists; today
   every type is scored the same regardless of moon phase.
7. **Seasonal preview ("what's coming up"):** a `--season` flag or GUI
   mode listing targets that will rise into a good observing window in
   the coming weeks/months, not just tonight — for planning ahead rather
   than only reacting to the current night.
8. **Finder charts / proximity maps:** a simple chart showing a target's
   position relative to nearby bright stars, from astropy coordinates +
   matplotlib. A navigation aid, complementing the polar `--chart` (which
   shows *when*, not *how to find it in the eyepiece/frame*).
9. **Integration time tracking in the session log:** once the session log
   (see the prioritized list above) exists, record planned vs. actual
   integration time per target per session, building a personal history
   over time.
10. **Southern-hemisphere correctness audit:** verify the RA/Dec →
    alt/az math and dark-window calculations carry no northern-hemisphere
    bias, and add test cases for southern-latitude sites. (Curating
    southern-sky *catalog content* stays explicitly out of scope — see
    below — this is purely about the math not silently assuming north.)
11. **Jargon-free descriptions ("beginner mode"):** an optional free-text,
    human-readable description per catalog entry, shown via a CLI
    `--verbose` flag or in the GUI, for anyone newer to the hobby than the
    current magnitude/size/type fields assume.
12. **Curated-shortlist mode:** an opt-in smaller, hand-picked subset of
    the catalog (Messier + a few standout Caldwell/NGC targets) as an
    alternative to evaluating everything — relief from choice overload for
    someone just starting out, while the full open-catalog ranking stays
    the default. Sits in real tension with the "evaluate everything,
    rank objectively" principle in CLAUDE.md, so only worth doing if it's
    clearly opt-in and never changes the default behavior.
13. **Web interface:** a lightweight browser front end (independent of the
    retired Streamlit MVP — see STATUS.md for why that one was dropped)
    for no-install, cross-device access. The CLI and native GUI would
    stay primary either way.
14. **Mobile-friendly output:** a shareable HTML/PDF report, or a
    terminal-friendly compact summary, for checking the plan on a phone
    at the eyepiece rather than needing a laptop open.
15. **Evening sequence instead of only a ranking:** order the shortlist
    into a timeline (target A 21:30–23:00, target B 23:00–01:30, …) and
    flag conflicts where two GO targets peak at the same time. A smart
    telescope shoots one target after another; the sequence would also
    be the natural order for the SkySafari export (priority #1 above).
16. **Seeing and transparency:** 7Timer's ASTRO product as an optional
    source in `weather/`, as extra `WeatherSummary` terms with tests.
    Transparency matters almost as much as cloud for deep sky at a
    suburban site. 7Timer data is for non-commercial use only.
17. **Week ahead:** `lotse week` (and a GUI view) with one row per night —
    darkness, Moon, clear window — as far as the 16-day forecast reaches,
    nights from three days out marked as less certain. For picking the
    night to drive to a dark site.
18. **Second weather opinion:** fetch a second model through Open-Meteo
    (e.g. ICON-D2 vs. ECMWF) and name the disagreement as a reason; the
    verdict still comes from the primary model. Models often diverge over
    central Europe, and saying so honestly fits the guiding principle.
19. **Clear-night notification:** a small launchd job, outside the engine
    in its own module, that runs the plan in the evening and posts a macOS
    notification when the night verdict (1) is GO.
20. **Shooting hints per rig:** optional per-rig filter/exposure fields
    (Seestar S30 Pro: light-pollution filter on for emission targets, off
    for broadband, 10 s frames), with the frame count computed from the
    clear window. The practical side of integration time estimation (4).
21. **Horizon from terrain data:** look up the surrounding terrain once per
    site (Open-Meteo's elevation API, Copernicus DEM 90 m) and propose it
    as a lower bound for the horizon profile. Terrain sees hills only,
    never trees or buildings, so it complements a hand-measured profile
    rather than replacing it — most useful for field sites that have none.
22. **More events:** meteor showers, lunar occultations, ISS passes, with
    a calendar export. Useful for public observing nights more than for
    imaging plans.
23. **Dark sites from light-pollution data:** a VIIRS-derived grid for the
    region, listing darker places within reach with an estimated Bortle
    class, complementing measured SQM values. Large effort (data volume,
    licensing), hence low.
24. **Menu-bar indicator:** a `QSystemTrayIcon` showing tonight's night
    verdict (1) at a glance. Only worth it once 1 exists.

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
- **Framing preview: camera view.** The framing preview (`lotse frame`,
  the GUI's "Framing preview…") shows a square, north-up sky cutout with
  the rig's frame drawn on it, so the rotated alt-az frame always fits and
  the surroundings stay visible. A second rendering cropped to the frame
  itself — the sensor's own aspect ratio, rotated the way the camera sees
  it at the best time (zenith up, not north) — would show the actual
  shot. Same geometry (`engine.framing_preview`), just a different crop.
- **Position angles in the catalog:** `Target` has a size but no
  position angle, so the framing preview draws each object's major axis
  as a dashed circle (its reach, not its shape) and leaves the true
  orientation to the survey image. A sourced `position_angle_deg` per
  entry (same sourcing rules as magnitude/size, see CLAUDE.md) would
  allow real ellipses — and an orientation-aware fit score for elongated
  targets like M31 on an alt-az rig.
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

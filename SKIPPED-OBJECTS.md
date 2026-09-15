# Catalog Import — Skipped Objects

Objects not carried over from the three book imports (Ruben Kier, *The 100
Best Astrophotography Targets*; Charles Bracken, *The Astrophotography
Planner*, 2nd ed.; Charles Bracken, *The Astrophotography Sky Atlas*, Object
Index pp. 90–140), kept here for future review. See also STATUS.md, section
`nachtlotse/data/catalog/`.

## Added to the catalog (in progress, block by block)

Now that `Target.magnitude: float | None` + `mag_unknown.yaml` exist
(roadmap item #1), most of the "no magnitude" entries below aren't
permanent exclusions any more — they just need a real, citable
`size_arcmin` sourced (coordinates too, re-verified against current
SIMBAD/OpenNGC rather than trusted from the original import pass). Moved
out of the sections below once added; removed from this list entirely,
not just marked.

**Block 1 (2026-09-15):**
- **IC 4606** ("Antares Nebula") → `mag_unknown.yaml`. Coordinates from
  SIMBAD (quality flag E); size (60′×40′) from French Wikipedia, since
  neither SIMBAD nor OpenNGC carries one.
- **Sh2-240** (Simeis 147, "Spaghetti Nebula") → `mag_unknown.yaml`.
  Coordinates from SIMBAD; size (~180′, i.e. ~3°) corroborated across
  Wikipedia, APOD, and the original Sharpless (1959) catalog value.
- **NGC 1555** (Hind's Variable Nebula) → **`mag_9_10.yaml`**, not
  `mag_unknown.yaml` — Wikipedia carries a real B-mag (9.98) that SIMBAD
  itself doesn't, which is enough sourcing per this project's own
  standard (see the Kier-import entries below: "no solid magnitude in
  OpenNGC, SIMBAD, *or Wikipedia*" is the actual exclusion bar). Size
  (0.5′) from Deep Sky Corner; a Chandra X-ray figure (~6″) for the same
  object measures a different, much smaller feature, not the nebula's
  photographic extent, so it isn't a competing value.

**Block 2 (2026-09-15):** the six small Orion-belt reflection nebulae →
`mag_unknown.yaml`. Coordinates from SIMBAD throughout. Sizes from SIMBAD's
own Dim field where present (IC 423, IC 426: 6.0′×3.5′ each); for the rest
(IC 424, IC 431, IC 432, IC 435), SIMBAD carried no Dim field, so sizes
came from go-astronomy.com's OpenNGC-derived major/minor-axis fields,
cross-checked against its own coordinates matching SIMBAD's closely on
every one of the six before trusting its size figures.

**Block 3 (2026-09-15):** the illuminating-star-magnitude conflation
cases.
- **IC 4592** (Blue Horsehead Nebula) → `mag_unknown.yaml`. Size (150′×60′)
  from Deep Sky Corner.
- **vdB 75** → `mag_unknown.yaml`, filed as **IC 444** (alias vdB 75).
  Correcting a mislabeling in this document: "vdB 75 (Foxfur Nebula)" was
  wrong — the real Foxfur Nebula is Sh2-273/NGC 2264, a different object
  in a different constellation (see below). SIMBAD's own "vdB 75" lookup
  resolves to the illuminating star (12 Gem) rather than a nebula entry;
  IC 444 is the same physical nebula under its own, separately cataloged
  SIMBAD entry. Size (~32′ dia.) from Wikipedia.
- **IC 1318** (Gamma Cygni Nebula) → `mag_unknown.yaml`. SIMBAD's own
  "IC 1318" position sits ~1.7° from every other source for this object;
  used Deep Sky Corner's Gamma-Cygni(Sadr)-centered coordinates paired
  with its own size (50′×30′) instead, to keep position and size
  self-consistent.
- **IC 1287** → `mag_unknown.yaml`. Size (20′×10′) from go-astronomy.com;
  B-Mag=6.10 reconfirmed as the illuminating star's, not the nebula's.
- **IC 348** → **`mag_7_8.yaml`**, not `mag_unknown.yaml` — a genuine
  surprise: SIMBAD's primary classification for IC 348 is *Open Cluster*,
  not the reflection nebula the original import assumed. Bracken's "mag
  3.8" is still the illuminating star Omicron Persei, but the young
  cluster itself has its own real, separately sourced magnitude (7.30,
  go-astronomy.com) and a sensible 7′ framing size — SIMBAD's own size
  field for IC 348 (480′) describes the surrounding molecular cloud, not
  the recognizable cluster.

**Block 4 (2026-09-15):** the remaining "no reliably sourced magnitude"
cases — single source per field (SIMBAD, plus one secondary lookup only
where SIMBAD had no Dim field), since nothing here came back implausible.
- **IC 417** (Spider Nebula), **IC 59**, **NGC 2174** (Monkey Head
  Nebula), **NGC 2023** → `mag_unknown.yaml` as originally reasoned —
  genuinely no magnitude anywhere.
- **IC 2177** (Seagull Nebula) → `mag_unknown.yaml`, filed at its own
  cataloged position/size (~13′, the compact "head"/NGC 2327 region), not
  the ~120′ full wing complex some wide-field images call by the same
  popular name.
- **NGC 1333** → **`mag_10_11.yaml`**, not `mag_unknown.yaml` — re-read
  the original reasoning: OpenNGC's B-Mag=10.90 rates the "Cl+N" (cluster
  + nebulosity) type, i.e. the same embedded object's own combined light,
  not an unrelated illuminating star's brightness like the other
  conflation cases in this document. Used as-is; Wikipedia's own
  infobox separately (and implausibly) lists V=5.6, not used.

## Pure Sharpless/CTB nebulae without a published integrated magnitude

**Block 5 (2026-09-15):** the six "individually verified" cases below →
added to the catalog, one source pass each (SIMBAD/Wikipedia).
- **Sh2-101** (Tulip Nebula) → **`mag_9_10.yaml`**, not `mag_unknown.yaml`
  — Wikipedia's infobox carries a real V=9.0 that SIMBAD doesn't.
- **Sh2-129** (Flying Bat Nebula), **Sh2-132** (Lion Nebula) →
  `mag_unknown.yaml` as originally reasoned, sizes from Wikipedia/web
  search (140′ and 42′×30′ respectively).
- **Sh2-157** (Lobster Claw Nebula) → `mag_unknown.yaml`. SIMBAD's own Dim
  field (3.32′×1.68′) turned out to measure a compact radio-bright core,
  not the full ~35′×40′ visible nebula (multiply corroborated) — caught
  because the SIMBAD figure looked implausibly small for a nebula
  popularly imaged as a large claw shape.
- **Sh2-276** (Barnard's Loop) → `mag_unknown.yaml`. Wikipedia's infobox
  claims V=5, implausible for a nebula famously invisible without
  narrowband filters and long exposure, and contradicted by SIMBAD
  (no magnitude/flux at all) — not used. Size (~10°) corroborated by both.
- **CTB 1 / Abell 85** (Garlic Nebula) → `mag_unknown.yaml`. Size (34.6′)
  from Abell's own 1966 catalog value.

**Block 6 (2026-09-15):** the rest of the previously-unlooked-up
Sharpless entries, now individually checked and added.
- **Sh2-206** → `mag_unknown.yaml`, filed as **NGC 1491** (its own real
  NGC designation, alias Sh2-206) — the NGC/IC-first convention this
  catalog otherwise follows throughout.
- **Sh2-264** (Lambda Orionis Ring), **Sh2-119** → `mag_unknown.yaml` as
  originally reasoned; sizes (390′ and 120′) from web search, both
  consistently cited.
- **Sh2-86** (previously listed here as "NGC 6820") → `mag_unknown.yaml`.
  Reconfirmed: OpenNGC's B-Mag=15.0 belongs to the tiny (30″) NGC 6820
  sub-feature, not the ~40′ nebula Bracken describes; catalog_id is
  "Sh2-86" with "NGC 6820" as an alias (it's colloquially used for the
  whole area even though it technically names only the sub-feature).
- **Sh2-126** → `mag_unknown.yaml`, filed as **"Great Lacerta Nebula"**
  — another mislabeling caught: this document's "Scarlet Letter Nebula"
  name is wrong for Sh2-126; the real Scarlet Letter Nebula is the
  unrelated Sh2-96. Size (180′) from web search.
- **Sh2-308** (Dolphin Nebula) → `mag_unknown.yaml`. SIMBAD's own
  "Sh2-308" lookup resolves straight to the central Wolf-Rayet star
  (HD 50896, V=6.91) — Wikipedia's V=7.0 is the same star's brightness,
  not the wind-bubble nebula's. Size (35′) from Wikipedia.
- **Sh2-261** (Lower's Nebula) → `mag_unknown.yaml`. Size (~50′)
  consistently cited across current sources; an older catalog value
  (10′×8′) describes only the brighter core.

**Block 7 (2026-09-15):** the six minor Sky-Atlas-only Sharpless entries
— 2 of 6 resolved.
- **Sh2-1** → `mag_unknown.yaml`, filed as **"Pi Scorpii Nebula"** (alias
  vdB 99). Size (150′, i.e. 2°30′) consistently cited.
- **Sh2-232** → `mag_unknown.yaml`. SIMBAD itself carries a real Dim
  field this time (45.63′), no secondary lookup needed.
- **Sh2-88, Sh2-134, Sh2-135, Sh2-230** — still no citable angular size
  found anywhere (only physical size + a distance estimate, sometimes
  itself a wide range e.g. 6,800–9,800 ly for Sh2-230); deriving an
  arcmin figure from those would compound two uncertain numbers into a
  computed value this catalog doesn't otherwise use anywhere — left open
  rather than doing that.

**Block 8 (2026-09-15):** all five Abell planetary nebulae → added to the
catalog, resolved via their disambiguating PN A66/PK designation (plain
"Abell N" collides in SIMBAD with George Abell's separate, much more
famous galaxy-cluster catalog — the same number means two different
kinds of object depending which catalog). Sizes and coordinates from
Deep Sky Corner throughout. Confirms rather than contradicts the original
"no published magnitude" finding: every one of the five lists a distinct
"C-Star" (central star) magnitude, not a nebula magnitude — Abell 33's
page briefly suggested a separate 15.5 "nebula" value identical to its
own C-star V-mag, too likely to be the same number restated to trust.

**Block 9 (2026-09-15):** the last four — this closes out the Sharpless/
CTB group entirely.
- **RCW 181** → `mag_unknown.yaml`. Size (6′) from web search; a widely
  cited "magnitude 14.6" couldn't be verified against a primary source
  (page blocked) and, given the Abell block's pattern of central-star
  magnitudes masquerading as the nebula's, wasn't used without that
  verification.
- **BFS63** — still no citable angular size found; stays open.
- **Fox Fur Nebula** (Sh2-273) — correctly excluded, not just
  unsourced: SIMBAD's own "Sh2-273" lookup resolves to the same broad
  NGC 2264 region already in this catalog (as the Christmas Tree
  Cluster, 11.4′). The Fox Fur is a popularly-imaged sub-feature of that
  same physical object, not a distinct one — adding it separately would
  duplicate an already-catalogued target, the same reasoning that
  already excludes IC 1318b from the Gamma Cygni complex above.
- **Perseus Molecular Cloud** — correctly excluded: a 6°×2° umbrella
  term for a whole star-forming complex, not a single framable target,
  and its two most notable sub-structures (IC 348, NGC 1333) are already
  in this catalog under their own entries (Block 3, Block 4 above).

## Dark nebulae — the Barnard/Lynds catalog carries no integrated magnitude

**Block 10 (2026-09-15):** dark nebulae are obscuration, not emission —
"no magnitude" isn't a gap here, it's definitional. All four → added.
- **Barnard 72** (Snake Nebula) → `mag_unknown.yaml`. Size (37′×17′) from
  web search.
- **Barnard 59/65–67** (Pipe Nebula) → `mag_unknown.yaml`, filed as
  **LDN 1773** — Wikipedia's own distinction is that B59/65-67 (aka
  LDN 1773) form specifically the *stem* (300′×60′); the *bowl* is the
  separate B78/LDN 42, not part of this entry and not added here.
- **Barnard 142/143** (Barnard's E) → `mag_unknown.yaml`, filed as
  **Barnard 142** (alias 143) under its common name "E Nebula". Size
  (30′) from Wikipedia.
- **LDN 1235** (Dark Shark) → `mag_unknown.yaml`. SIMBAD's own Dim field
  (10.2′×4.2′) covers specifically the "nose" feature that LDN 1235
  catalogs — not the full, much larger shark silhouette some wide-field
  images popularly call by the same name.

Also resolved this block: **NGC 7822 / Ced 214 / Sh2-171 complex** (from
the "no magnitude entry in OpenNGC at all" section, since merged into
here) → `mag_unknown.yaml`, filed under its own real NGC designation
(NGC 7822, aliases Ced 214 and Sh2-171) — SIMBAD carries real coordinates
and a size (22.8′) for it directly.

## No formal catalog designation at all
- OU4 (Squid Nebula) — discovered and named purely by an amateur:
  - The Squid Nebula is Ou4, a very faint nebula in the constellation Cepheus. It lies within the Flying Bat Nebula (Sh 2-129) and was discovered in 2011 by amateur astronomer Nicolas Outters.
- IC 1318b — an informal sub-region of the Gamma Cygni/IC 1318 complex
  (now in the catalog, see "Added to the catalog" above), but IC 1318b
  itself still has no catalog entry of its own.

## The catalog designation itself is doubtful (Sky Atlas pass)
Beyond a missing magnitude: OpenNGC/NED doubt that the designation reliably
points to the intended object at all.

**Rechecked 2026-09-15 against current SIMBAD/NED** (roadmap item #1 — the
only reason this small set was worth a future revisit at all): 3 of the
original 5 have since resolved to a real, catalogable object and are now
in the catalog (see "Added to the catalog" above — IC 4606, NGC 1555, and
Simeis 147 as Sh2-240). The two below remain excluded, unchanged. See
`catalog_sourcing_policy` in CLAUDE.md's Coding conventions for the
sequential-query/conflicting-value rules this recheck followed.

- **NGC 6874** — still unresolved. Current SIMBAD: "Object of Unknown
  Nature", no coordinates at all. Same tangle as before (NED:
  "Identification as NGC 6682 is not certain" on the related NGC
  6874/6882/6885 entries). Remains excluded.
- **IC 1316** — still unresolved. Current NED: still "Nothing here;
  nominal position" (RA 20h22m26s, Dec +06°30'06", 150″ uncertainty
  ellipse), unchanged from the original finding. (A SIMBAD-page summary
  during this recheck briefly claimed "IC 1316 = NGC 6901, a barred
  spiral galaxy" — cross-checked directly against NED and rejected; that
  claim was fabricated by the page-summarization step, not something NED
  actually says. Noted here, and in CLAUDE.md's sourcing policy, as a
  reminder to verify surprising findings against a second source.)
  Remains excluded.

## Closed out from the Kier import (no longer a roadmap item)
- NGC 2170 (Angel Nebula) — no solid magnitude in OpenNGC, SIMBAD, or
  Wikipedia; verified directly, not a research gap
- IC 410 (Tadpole Nebula) — carried by OpenNGC/NED as a duplicate of the
  magnitude of its embedded cluster NGC 1893; structurally the same pattern
  as the other star/cluster magnitude conflations above

## Conclusion after three book imports
Most of this list is a structural outcome (diffuse emission/dark nebulae and
Abell planetary nebulae essentially never get a published object magnitude),
not a temporary research gap — more searching won't change it.

The five designation-doubtful cases were rechecked on 2026-09-15. Three
resolved — IC 4606, NGC 1555, and Simeis 147 (as Sh2-240) are now
confirmed real, catalogable objects and, as of Block 1, already in the
catalog (see "Added to the catalog" above). Two remain excluded on their
original grounds: IC 1316 and NGC 6874 still have no real position/data
at all in NED/SIMBAD. No further lookups are expected to change either of
those two.

The rest of this list (diffuse emission/dark nebulae, Abell planetary
nebulae, star/sub-feature magnitude conflations) is no longer a permanent
exclusion either — `Target.magnitude: float | None` + `mag_unknown.yaml`
accept exactly this case, as long as a real, citable size is sourced.
Blocks 1–10 (2026-09-15, see "Added to the catalog" above) worked through
essentially all of it — the illuminating-star-magnitude conflations, the
Sharpless/CTB nebulae, the Abell planetary nebulae, and the Barnard/Lynds
dark nebulae — turning up two more mislabelings along the way (vdB 75
tagged as "Foxfur Nebula", Sh2-126 tagged as "Scarlet Letter Nebula" —
both wrong; corrected in their catalog entries) and a few genuine
surprises where the "no magnitude" premise didn't hold at all (Sh2-101,
NGC 1555, NGC 1333, IC 348 — see their entries in "Added to the catalog").

What's left, all for concrete, specific reasons rather than "not yet
looked at":
- **No citable angular size found anywhere**, despite a real lookup pass:
  BFS63, Sh2-88, Sh2-134, Sh2-135, Sh2-230 (5 objects).
- **Not real, catalogable objects at all** — no position/data exists,
  not expected to change with more searching: IC 1316, NGC 6874.
- **Structurally excluded, not just unsourced** — each would duplicate or
  misrepresent an object already in this catalog: IC 1318b (sub-region of
  the already-catalogued Gamma Cygni/IC 1318), Fox Fur Nebula (sub-region
  of the already-catalogued NGC 2264), Perseus Molecular Cloud (an
  umbrella term for a complex whose notable sub-structures, IC 348 and
  NGC 1333, are already catalogued separately), OU4 (no formal catalog
  designation of its own).
- **Deliberately closed, not a roadmap item**: NGC 2170, IC 410 (see
  "Closed out from the Kier import" below).

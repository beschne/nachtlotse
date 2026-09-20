# Catalog Import — Skipped Objects

Objects not carried over from the three book imports (Ruben Kier, *The 100
Best Astrophotography Targets*; Charles Bracken, *The Astrophotography
Planner*, 2nd ed.; Charles Bracken, *The Astrophotography Sky Atlas*, Object
Index pp. 90–140), kept here for future review. See also STATUS.md, section
`nachtlotse/data/catalog/`.

Objects that have since been added to the catalog are removed from this
list entirely — their sourcing lives as a comment next to the entry in the
relevant `mag_*.yaml` file, not here. This file only tracks what's still
**not** in the catalog, and why.

## Still open: no citable angular size found anywhere

Real, catalogable objects — `Target.magnitude: float | None` +
`mag_unknown.yaml` accept a missing magnitude — but no citable
`size_arcmin` found despite a real lookup pass. Physical size + a distance
estimate exists for some, but deriving an arcmin figure from those would
compound two uncertain numbers into a computed value this catalog doesn't
otherwise use anywhere.

- BFS63
- Sh2-88, Sh2-134, Sh2-135, Sh2-230 (some only have a physical-size +
  distance estimate, itself sometimes a wide range, e.g. 6,800–9,800 ly
  for Sh2-230)

## Not real, catalogable objects — no position/data at all

Rechecked against current SIMBAD/NED on 2026-09-15; not expected to change
with more searching. See `catalog_sourcing_policy` in CLAUDE.md's Coding
conventions for the sequential-query/conflicting-value rules this recheck
followed.

- **IC 1316** — current NED: still "Nothing here; nominal position" (RA
  20h22m26s, Dec +06°30'06", 150″ uncertainty ellipse), unchanged from the
  original finding; reconfirmed again 2026-09-20 (prompted by a fresh NED
  link) via OpenNGC's own `NGC.csv`, whose NED-notes field for IC1316
  carries the identical phrase — a genuine absence, not a research gap.
  (A SIMBAD-page summary during the 2026-09-15 recheck briefly claimed
  "IC 1316 = NGC 6901, a barred spiral galaxy" — cross-checked directly
  against NED and rejected; that claim was fabricated by the
  page-summarization step, not something NED actually says. Noted here,
  and in CLAUDE.md's sourcing policy, as a reminder to verify surprising
  findings against a second source.)

NGC 6874 was previously listed here too ("Object of Unknown Nature" per
SIMBAD) — a 2026-09-20 recheck (prompted by user-supplied German
Wikipedia/OpenNGC/NED links) found that conclusion wrong: it does have a
real, citable position and size, just no sourced magnitude. It's now in
the catalog (`mag_unknown.yaml`, Block 12) — see the comment there for
the full sourcing.

## No formal catalog designation at all

- **OU4** (Squid Nebula) — discovered and named purely by an amateur
  (Nicolas Outters, 2011); lies within Sh2-129 (Flying Bat Nebula), which
  is in the catalog under its own designation. Cross-referenced directly
  in that entry's comment (`mag_unknown.yaml`) as of 2026-09-20, along
  with its central star (HD 202214).
- **IC 1318b** — an informal sub-region of the Gamma Cygni/IC 1318
  complex (IC 1318 itself is in the catalog); IC 1318b has no catalog
  entry of its own. Cross-referenced directly in that entry's comment
  (`mag_unknown.yaml`) as of 2026-09-20.

## Structurally excluded — would duplicate an already-catalogued object

- **Fox Fur Nebula** (Sh2-273) — SIMBAD's own "Sh2-273" lookup resolves
  to the same broad NGC 2264 region already in the catalog (as the
  Christmas Tree Cluster, 11.4′). A popularly-imaged sub-feature of that
  object, not a distinct one.
- **Perseus Molecular Cloud** — a 6°×2° umbrella term for a whole
  star-forming complex, not a single framable target. Its two most
  notable sub-structures (IC 348, NGC 1333) are already in the catalog
  under their own entries.

## Closed out from the Kier import (no longer a roadmap item)

- **NGC 2170** (Angel Nebula) — no solid magnitude in OpenNGC, SIMBAD, or
  Wikipedia; verified directly, not a research gap.
- **IC 410** (Tadpole Nebula) — carried by OpenNGC/NED as a duplicate of
  the magnitude of its embedded cluster NGC 1893; structurally the same
  pattern as the star/cluster magnitude conflations resolved elsewhere.

## Conclusion

What's left is open for concrete, specific reasons rather than "not yet
looked at":

- **No citable angular size found anywhere**, despite a real lookup pass:
  BFS63, Sh2-88, Sh2-134, Sh2-135, Sh2-230 (5 objects).
- **Not a real, catalogable object at all** — no position/data exists, not
  expected to change with more searching: IC 1316 (NGC 6874 turned out not
  to belong here after all — see above — and is now in the catalog).
- **Structurally excluded, not just unsourced** — each would duplicate or
  misrepresent an object already in this catalog: IC 1318b (sub-region of
  the already-catalogued Gamma Cygni/IC 1318), Fox Fur Nebula (sub-region
  of the already-catalogued NGC 2264), Perseus Molecular Cloud (an
  umbrella term whose notable sub-structures, IC 348 and NGC 1333, are
  already catalogued separately), OU4 (no formal catalog designation of
  its own).
- **Deliberately closed, not a roadmap item**: NGC 2170, IC 410 (see
  "Closed out from the Kier import" above).

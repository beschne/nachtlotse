# Catalog Import — Skipped Objects

Objects not carried over from the three book imports (Ruben Kier, *The 100
Best Astrophotography Targets*; Charles Bracken, *The Astrophotography
Planner*, 2nd ed.; Charles Bracken, *The Astrophotography Sky Atlas*, Object
Index pp. 90–140), kept here for future review. See also STATUS.md, section
`nachtlotse/data/catalog/`.

## No reliably sourced object magnitude found
- IC 417 (Spider Nebula)
- IC 59
- NGC 1333 — OpenNGC does list B-Mag=10.90, but under type "Cl+N" (cluster +
  nebulosity rated together); not unambiguously the nebula's own magnitude,
  consistent with the original rejection
- NGC 2174 (Monkey's Head Nebula)
- IC 2177 (Seagull Nebula) — confirmed again in the Sky Atlas pass: the
  sub-designation NGC 2327 (the "Seagull Nebula" body) also carries no
  magnitude in OpenNGC
- NGC 2023 — a well-known, frequently imaged reflection nebula next to the
  Horsehead, but neither OpenNGC nor SIMBAD lists a magnitude for the nebula
  itself (SIMBAD points instead to the star HD 37903) (Sky Atlas pass)
- IC 1318b — an informal sub-region of the already-excluded Gamma
  Cygni/IC 1318 complex, no catalog entry of its own (Sky Atlas pass)

## The only "magnitude" found belonged to the illuminating star, not the nebula
- IC 4592 (Blue Horsehead Nebula) — OpenNGC's value is the star Nu Scorpii
- vdB 75 (Foxfur Nebula) — the SIMBAD entry is the star *12 Gem
- IC 1318 (Gamma Cygni Nebula) — OpenNGC's entry resolves to the star Gamma
  Cygni, not the nebula complex
- IC 1287 — OpenNGC's B-Mag=6.10 lines up exactly with Bracken's own
  description, "reflection nebula around mag 6.0 star"; the magnitude is the
  illuminating star's (Sky Atlas pass)
- IC 348 — Bracken's "mag 3.8" refers to the illuminating star Omicron
  Persei ("Attik"), not the nebula itself; OpenNGC carries no magnitude of
  its own for IC 348 (Sky Atlas pass)
- IC 423, IC 424, IC 426, IC 431, IC 432, IC 435 — small reflection nebulae
  along Orion's belt, no magnitude of their own in OpenNGC (Sky Atlas pass)

## Pure Sharpless/CTB nebulae without a published integrated magnitude
Individually verified:
- Sh2-101 (Tulip Nebula)
- Sh2-129 (Flying Bat Nebula)
- Sh2-132 (Lion Nebula)
- Sh2-157 (Lobster Claw Nebula)
- Sh2-276 (Barnard's Loop)
- CTB 1 / Abell 85 (Garlic Nebula)
- Simeis 147 — not resolvable in SIMBAD under that name, but **resolves
  cleanly under its Sharpless alias, Sh 2-240** (2026-09-15 SIMBAD
  recheck): real coordinates (05 41 06.0 +28 05 00), classified HII
  Region, no magnitude/flux listed. No longer a designation question —
  a `mag_unknown.yaml` candidate (catalog_id "Sh2-240", alias "Simeis
  147") once a sourced size is found; see the "designation is doubtful"
  section below for the other 2026-09-15 recheck findings.

Skipped by the same confirmed pattern, without a fresh individual lookup:
- Sh2-206
- Sh2-264 (Lambda Orionis Ring)
- Sh2-86 (NGC 6820) — OpenNGC does carry B-Mag=15.0, but for a 0.5′ feature
  inside what is actually a 30′ nebula (per Bracken); the magnitude belongs
  to a small knot, not the pictured object — the same conflation shape as
  the star cases above, just with a sub-feature instead of a star
- Sh2-119
- Sh2-126 (Scarlet Letter Nebula)
- Sh2-308 (Dolphin Nebula)
- Sh2-261 (Lower's Nebula)
- Sh2-1, Sh2-88, Sh2-134, Sh2-135, Sh2-230, Sh2-232, Sh2-240 (Sky Atlas pass,
  no OpenNGC entry, no published integrated magnitude)
- Abell 7, Abell 29, Abell 33, Abell 35, Abell 36 (Sky Atlas pass; like
  virtually all Abell planetary nebulae, no published magnitude)
- BFS63, RCW 181, Fox Fur Nebula (= Sh2-273, part of NGC 2264), Perseus
  Molecular Cloud (Sky Atlas pass; RCW 181 and Perseus Molecular Cloud each
  checked individually via SIMBAD — no magnitude listed)

## Dark nebulae — the Barnard/Lynds catalog carries no integrated magnitude
- Barnard 72 (Snake Nebula)
- Barnard 59/65–67 (Pipe Nebula)
- Barnard 142/143 (Barnard's E)
- LDN 1235 (Dark Shark)

## No formal catalog designation at all
- OU4 (Squid Nebula) — discovered and named purely by an amateur:
  - The Squid Nebula is Ou4, a very faint nebula in the constellation Cepheus. It lies within the Flying Bat Nebula (Sh 2-129) and was discovered in 2011 by amateur astronomer Nicolas Outters.

## No magnitude entry in OpenNGC at all
- NGC 7822 / Ced 214 / Sh2-171 complex

## The catalog designation itself is doubtful (Sky Atlas pass)
Beyond a missing magnitude: OpenNGC/NED doubt that the designation reliably
points to the intended object at all.

**Rechecked 2026-09-15 against current SIMBAD/NED** (roadmap item #1 — the
only reason this small set was worth a future revisit at all): 3 of the 4
below have since resolved to a real, catalogable object and moved out of
this section — the designation dispute is settled, they're just still
missing a magnitude (candidates for `mag_unknown.yaml` once a sourced size
is found, alongside Simeis 147 above). The other one (NGC 6874) is
unchanged. See `catalog_sourcing_policy` in CLAUDE.md's Coding conventions
for the sequential-query/conflicting-value rules this recheck followed.

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

Resolved, moved to "no magnitude" status:
- **IC 4606 ("Antares Nebula")** — current SIMBAD classifies it as a real
  HII Region (aliases LBN 1107, LBN 351.76+15.00), 7 references spanning
  1850–2026, coordinates 16h29m00s −26°36'00" (quality flag E, ≥10″
  uncertain — still well inside this project's ~1′ precision need). No
  mention of "nothing here" or NGC 6144 confusion in the current record.
  Still no magnitude/flux listed.
- **NGC 1555 (Hind's Variable Nebula)** — current SIMBAD treats it as a
  real object: 9 identifiers (incl. HH 155, Sh2-238, Ced 32b), classified
  Herbig-Haro Object, cross-referenced to the T Tauri variable star it's
  illuminated by. This matches its own name and well-documented history —
  a nebula that genuinely brightens and fades with its illuminating star,
  observed and lost repeatedly since 1852 (see also the neighboring
  Struve's Lost Nebula, NGC 1554, same phenomenon). The original "Strauss
  et al. (1992): just a star" note could not be independently
  re-confirmed this pass (NED timed out repeatedly on this object), but
  current SIMBAD data and multiple independent sources describe a real,
  historically documented variable nebula, not a misidentified star. No
  magnitude/flux listed in SIMBAD.

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

The five designation-doubtful cases were rechecked on 2026-09-15 (roadmap
item #1). Three resolved — IC 4606, NGC 1555, and Simeis 147 (as Sh2-240)
are now confirmed real, catalogable objects; the "designation doubtful"
question is settled, all that's left is a missing magnitude, which
`Target.magnitude: float | None` + `mag_unknown.yaml` (roadmap item #2) can
now hold without inventing a number — they're candidates for that file once
someone sources a real size for each. Two remain excluded on their original
grounds: IC 1316 and NGC 6874 still have no real position/data at all in
NED/SIMBAD. No further lookups are expected to change either of those two.

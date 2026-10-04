**Deutsch:** [Der Katalog](Der-Katalog)

Nachtlotse comes with a curated catalog of 236 deep-sky objects: 63 Messier
objects and 173 other well-known imaging targets from NGC, IC, Sharpless,
Abell, van den Bergh and Caldwell.

| Kind | Count |
|---|---|
| galaxies | 87 |
| emission nebulae | 58 |
| open clusters | 38 |
| planetary nebulae | 30 |
| reflection nebulae | 28 |
| galaxy groups | 20 |
| dark nebulae | 9 |
| globular clusters | 8 |
| variable stars | 1 (T CrB) |

Some objects count as more than one kind (M42 is an emission and a
reflection nebula), so the counts add up to more than 236.

## Where the data comes from

The list started from the Messier catalog and was extended with the targets
in Ruben Kier's "The 100 Best Astrophotography Targets" and Charles
Bracken's "The Astrophotography Planner" and "The Astrophotography Sky
Atlas". Coordinates, sizes and magnitudes were checked against OpenNGC, and
against SIMBAD and NED where OpenNGC had nothing.

Each physical object appears once. Other designations go into `aliases`, so
M31 is also found as NGC 224. Coordinates are J2000 and accurate to about an
arcminute, enough for planning, not for pointing a telescope.

## Unknown values stay unknown

For 46 objects no reliable integrated magnitude exists, mostly large faint
emission and dark nebulae. They keep their entry without a magnitude rather
than with an invented one. Objects that could be found neither with a
magnitude nor with a reliable size were left out. `SKIPPED-OBJECTS.md` in
the repository lists them with the reasons.

The catalog has no orientation (position angle) for elongated objects. The
[Framing Preview](Framing-Preview) therefore draws their size as a circle.

## The files

The catalog lives in `nachtlotse/data/catalog/` as YAML files sorted by
brightness (`mag_lt_6.yaml` up to `mag_15_16.yaml`, plus `mag_unknown.yaml`).
Nachtlotse loads them brightest first, which is why a low `--limit` drops the
faintest objects first.

Your own favorites are not stored here but in a local file, see
[Favorites](Favorites).

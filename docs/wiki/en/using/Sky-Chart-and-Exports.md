**Deutsch:** [Himmelskarte und Export](Himmelskarte-und-Export)

## The sky chart

The Sky chart tab shows the shortlist on a round map of the sky. The center
is the zenith, the edge is the horizon, north is up. The grey area is the
part of the sky your horizon blocks.

Each target is drawn as its path through the night, colored by its verdict.
A dot marks its best time, in its own color so you can tell targets apart in
the legend. Favorites get a star instead of a dot. The Moon has its own path
and a small icon showing its phase.

With `-`, `+` and Fit you zoom the chart.

![The sky chart](https://raw.githubusercontent.com/wiki/beschne/nachtlotse/images/gui-sky-chart.png)

From the command line, `lotse plan --chart` writes the chart as a PNG
(`nachtlotse-shortlist.png` in the current folder, or a path you give). It
needs the `charts` extra.

## Exports from the app

Every screen in the app has an export button:

| Screen | Export |
|---|---|
| Shortlist, All ranked | CSV, SkySafari list |
| Events | SkySafari list |
| Sky chart | PNG |
| Briefing | text file |
| Sites, Rigs | text file |
| Framing preview | PNG |

The save dialog starts in the `exports/` folder of the repository.

## SkySafari lists

The SkySafari export writes an observing list (`.skylist`) that you open in
SkySafari on your phone or tablet, so tonight's targets are at hand at the
telescope. In the app, use Export SkySafari on the Shortlist, All ranked or
Events tab. From the command line, `lotse plan --skylist` writes the list
(`nachtlotse.skylist` in the current folder, or a path you give).

What goes into the list:

- Shortlist: the shortlisted targets, then the comets, supernovae and novae
  that are observable tonight. `--skylist-scope ranked` writes the whole
  ranking instead of the shortlist.
- All ranked: every ranked target, then the same events.
- Events: only the events observable tonight.

Catalog objects and comets open in SkySafari like any other object. Messier
and NGC objects are found by name and catalog number, comets by name.

Supernovae and novae are not in SkySafari's catalogs, and SkySafari can't
create objects of your own. They show up greyed out in the list and you
can't select them. To still tell you where to point, their J2000
coordinates are part of the name, for example
`SN 2026abc (RA 12h34m Dec +12d30m J2000)`.

This was checked with SkySafari 6.

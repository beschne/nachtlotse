# Sky Chart and Exports

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

![The sky chart](images/gui-sky-chart.png)

From the command line, `lotse plan --chart` writes the chart as a PNG
(`nachtlotse-shortlist.png` in the current folder, or a path you give). It
needs the `charts` extra.

## Exports from the app

Every screen in the app has an export button:

| Screen | Export |
|---|---|
| Shortlist, All ranked | CSV |
| Sky chart | PNG |
| Briefing | text file |
| Sites, Rigs | text file |
| Framing preview | PNG |

The save dialog starts in the `exports/` folder of the repository.

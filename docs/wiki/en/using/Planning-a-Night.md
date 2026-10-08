**Deutsch:** [Eine Nacht planen](Eine-Nacht-planen)

```bash
uv run lotse plan                                  # tonight, first site, first rig
uv run lotse plan --site Feldberg --rig S30P --date 2026-11-14
```

In the app: pick site, rig and date in the sidebar and press Re-plan.

## What you get

The header shows the dark window (from the end of evening twilight to the
start of morning twilight, see [Dark Window](Dark-Window)), the Moon's phase
and rise or set time, and the weather forecast for that window with an
hour-by-hour cloud bar.

Then comes the shortlist: the five best targets of the night, each with a
verdict (GO, MARGINAL or SKIP) and the reasons behind it. [Verdicts](Verdicts)
explains how they come about. Your [favorites](Favorites) are added after the
top five if they're up.

Below that is the full ranking of everything that is observable that night.
The columns are:

| Column | Meaning |
|---|---|
| Alt, Az | altitude and direction at the best time |
| Fit | how well the target fills your frame, 0 to 1 |
| Reach | how well its surface brightness stands out against your sky, 0 to 1 |
| Best | the best time to shoot it (the highest point that clears all limits) |

[How Ranking Works](How-Ranking-Works) explains Fit and Reach. In the app,
the Shortlist and All ranked tabs show the same tables. Hover over a row to
see the verdict reasons.

At the end comes the current-events block with comets, supernovae and novae,
see [Current Events](Current-Events).

## Groups

Targets that are close enough to share one frame of your rig, like M81 and
M82, appear as one entry with both names. You don't have to do anything for
that.

## Useful options

`--date YYYY-MM-DD` plans another night. Weather is only available up to 16
days ahead, the rest of the plan works for any date.

`--type galaxy` limits the list to one kind of object. You can repeat it:
`--type galaxy --type globular_cluster`.

`--limit N` checks only the N brightest catalog objects (default 50,
`--limit 0` for all 236). The full catalog takes about 3 seconds. In the
app this is the EVALUATE field.

`--best-rig` tries every rig you have configured for every target and keeps
the one that frames it best. Each row then names its rig. This option can't
be combined with `--rig`, `--chart` or `--skylist`, and it doesn't build groups.

`--chart`, `--skylist` and `--prose` are described in [Sky Chart and Exports](Sky-Chart-and-Exports)
and [Nightly Briefing](Nightly-Briefing). All options are listed in the
[CLI Reference](CLI-Reference).

## Framing a target

To see how a target from the list fits into your frame, use `lotse frame`
or, in the app, double-click a row. See [Framing Preview](Framing-Preview).

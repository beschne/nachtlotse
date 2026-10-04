**Deutsch:** [Erster Start](Erster-Start)

Once [Installation](Installation) is done and your [sites](Configuring-Sites)
and [rigs](Configuring-Rigs) are in place:

```bash
uv run lotse sites     # your sites as Nachtlotse reads them, check these first
uv run lotse rigs      # your rigs with field of view and pixel scale
uv run lotse plan      # tonight's list for your first site and first rig
```

The very first run downloads the JPL ephemeris file `de421.bsp` (about
17 MB) into `.cache/skyfield/`. That needs internet once. After that the
planner runs offline. Only weather, current events and sky images need a
connection, see [Offline and Caching](Offline-and-Caching).

## Check the installation

```bash
uv run pytest
```

The tests check the engine against known astronomical values. They don't
read your own site and rig files and never go online, so they pass either
way.

## Useful options for the first day

```bash
uv run lotse plan --site "Großer Feldberg" --rig S30P   # other site and rig
uv run lotse plan --date 2026-11-14     # another night
uv run lotse plan --limit 0             # check the whole catalog
uv run lotse plan --type galaxy         # one kind of object only (can repeat)
uv run lotse events                     # comets, supernovae, novae tonight
uv run lotse best-sky --radius-km 50    # which of your sites is clearest
```

`--site` and `--rig` take a name, an alias or a unique part of either.

## The app

```bash
uv sync --extra gui    # once
uv run lotse gui
```

The app uses the same engine and your same sites and rigs. There is no demo
data. If a table is empty, nothing is up. Next: [Planning a Night](Planning-a-Night).

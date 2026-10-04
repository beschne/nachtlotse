# CLI Reference

**Deutsch:** [Befehlsreferenz](Befehlsreferenz)

All commands start with `uv run lotse`. `uv run lotse <command> --help`
prints the same information.

Wherever a command takes `--site` or `--rig`, you can use a name, an alias
or a unique part of either. Without them, the first site and the first rig
in your files are used. `--date` is always `YYYY-MM-DD`, local to the site,
and defaults to tonight.

## lotse plan

Ranks the catalog for one night and gives verdicts. See [Planning a Night](Planning-a-Night).

| Option | Meaning |
|---|---|
| `--site`, `--rig`, `--date` | site, rig and night |
| `--type CATEGORY` | only this kind of object; can be repeated. Categories: `emission_nebula`, `reflection_nebula`, `planetary_nebula`, `dark_nebula`, `galaxy`, `galaxy_group`, `open_cluster`, `globular_cluster`, `variable_star` |
| `--limit N` | check only the N brightest catalog objects (default 50, 0 for all) |
| `--chart [PATH]` | write the sky chart as a PNG (default `nachtlotse-shortlist.png`); needs `charts` |
| `--no-events` | leave out comets, supernovae and novae |
| `--best-rig` | choose the best rig per target instead of using one; not with `--rig` or `--chart` |
| `--prose` | add a written briefing; needs `prose` and an API key |

## lotse events

Lists current comets, supernovae and novae: the ones observable that night
and all others with the reason. See [Current Events](Current-Events).
Options: `--site`, `--rig`, `--date`.

## lotse frame TARGET...

Shows how one or more targets fit into the rig's frame. A target can be a
catalog ID, alias or name (`M31`, `"NGC 224"`) or a current event (`161P`,
`"C/2026 A2"`, `2026aaiv`). See [Framing Preview](Framing-Preview).

| Option | Meaning |
|---|---|
| `--site`, `--rig`, `--date` | site, rig and night |
| `--out PATH` | where to write the PNG (default `nachtlotse-frame-<target>.png`); needs `charts` |
| `--no-survey` | don't fetch a sky image |

## lotse best-sky

Compares the cloud forecast of your sites. See [Best Sky](Best-Sky).

| Option | Meaning |
|---|---|
| `--site` | reference site |
| `--radius-km KM` | only sites within this distance |
| `--date` | night |

## lotse sites, lotse rigs

List your configured sites and rigs as Nachtlotse reads them. Rigs come with
field of view, pixel scale and a rough limiting magnitude.

## lotse gui

Starts the Mac app. Needs the `gui` extra.

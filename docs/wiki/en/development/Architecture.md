**Deutsch:** [Architektur](Architektur)

Nachtlotse is written in Python. The code is split into layers with a clear
rule: the engine does all astronomy and knows nothing about files, network
or screens.

```
nachtlotse/
├── engine/          # pure calculations, no files, no network
│   ├── ephemeris.py       # positions via skyfield, comet positions
│   ├── constraints.py     # dark window, altitude, Moon, horizon
│   ├── framing.py         # field of view, fit, reach, field rotation, limits
│   ├── framing_preview.py # frame layout on the sky
│   ├── grouping.py        # targets sharing one frame
│   ├── comets.py          # comets as rankable targets
│   ├── scoring.py         # verdicts
│   └── models.py          # data classes: Site, Rig, Target, ...
├── data/            # catalog, your sites/rigs/favorites
├── weather/         # Open-Meteo client
├── events/          # MPC, COBS, Rochester, TNS clients
├── planning.py      # puts engine, data, weather and events together
├── sky_survey.py    # sky images for the framing preview
├── charting.py, chart_export.py, frame_export.py   # charts and PNGs
├── best_sky.py      # site comparison
├── prose.py         # optional briefing via the Claude API
├── gui/             # the Mac app (PySide6)
└── cli.py           # the command line
```

Dependencies point one way: `cli.py` and `gui/` use `planning`, which uses
`engine`, `data`, `weather` and `events`. The engine imports none of them.
PySide6 is only loaded when you start the app.

Engine functions are pure: the same input always gives the same output.
Values that are the same for every target in a night (dark window, Sun and
Moon positions) are computed once and remembered, which is why the whole
catalog takes about 3 seconds.

Times are always timezone-aware and in UTC inside, local time only on
screen. Numbers carry their unit in the name (`focal_length_mm`, `alt_deg`).

More detail, module by module, is in `STATUS.md` in the repository. The
project's rules for contributors (and for Claude Code) are in `CLAUDE.md`.

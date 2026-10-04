# Nachtlotse

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey)
![UI: PySide6/Qt](https://img.shields.io/badge/UI-PySide6%2FQt-41cd52)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Vibe Coding: Claude Sonnet 5](https://img.shields.io/badge/Vibe%20Coding-Claude%20Sonnet%205-c96442)

English · [Deutsch](README.de.md)

Nachtlotse is German for "night pilot". It answers one question for
astrophotographers: what should I shoot tonight?

You tell it where you are and what equipment you use. It works out the sky
over your site for that night and gives you a short list of targets, each
with a verdict (GO, MARGINAL or SKIP) and the reasons for it. It takes your
real horizon, your camera's field of view, the Moon, the weather forecast
and how dark the night gets into account. It also lists comets, supernovae
and novae that are bright enough right now, and shows how a target fits
into your camera frame.

All astronomy is calculated from JPL ephemerides and tested against known
values. Nothing is guessed.

<p align="center">
  <img src="screenshots/gui-shortlist.png" alt="Nachtlotse app: the Shortlist tab" width="49%">
  <img src="screenshots/gui-sky-chart.png" alt="Nachtlotse app: the Sky chart tab" width="49%">
</p>

<p align="center"><sub>Same plan, two views: Volkssternwarte Hochtaunus, TEC AP 160/1120 f/7 FL, the night of September 25.</sub></p>

## Documentation

The full documentation is in the **[wiki](https://github.com/beschne/nachtlotse/wiki)**,
in English and German.

- [Installation](https://github.com/beschne/nachtlotse/wiki/Installation) and [First Run](https://github.com/beschne/nachtlotse/wiki/First-Run)
- [Planning a Night](https://github.com/beschne/nachtlotse/wiki/Planning-a-Night), [Current Events](https://github.com/beschne/nachtlotse/wiki/Current-Events), [Framing Preview](https://github.com/beschne/nachtlotse/wiki/Framing-Preview), [Best Sky](https://github.com/beschne/nachtlotse/wiki/Best-Sky)
- [How Ranking Works](https://github.com/beschne/nachtlotse/wiki/How-Ranking-Works) and [Verdicts](https://github.com/beschne/nachtlotse/wiki/Verdicts)
- [CLI Reference](https://github.com/beschne/nachtlotse/wiki/CLI-Reference)
- [Troubleshooting](https://github.com/beschne/nachtlotse/wiki/Troubleshooting) and [FAQ](https://github.com/beschne/nachtlotse/wiki/FAQ)

## Quickstart

Needs macOS and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/beschne/nachtlotse.git
cd nachtlotse
uv sync
cp nachtlotse/data/sites_local.template.yaml nachtlotse/data/sites_local.yaml
cp nachtlotse/data/rigs_local.template.yaml nachtlotse/data/rigs_local.yaml
# edit both files: your own site and your own equipment
uv run lotse plan          # tonight's list on the command line
uv sync --extra gui && uv run lotse gui    # or the Mac app
```

## For developers

The documentation sources live in [`docs/wiki/`](docs/wiki/) and are
published with `scripts/publish_wiki.py`. Architecture and project rules are
in [CLAUDE.md](./CLAUDE.md), the module-by-module state in
[STATUS.md](./STATUS.md), plans in [ROADMAP.md](./ROADMAP.md).

```bash
uv run pytest        # tests (offline, about 20 seconds)
uv run ruff check .  # lint
```

## License

[MIT](./LICENSE)

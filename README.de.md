# Nachtlotse

![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)
![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey)
![UI: PySide6/Qt](https://img.shields.io/badge/UI-PySide6%2FQt-41cd52)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Vibe Coding: Claude Sonnet 5](https://img.shields.io/badge/Vibe%20Coding-Claude%20Sonnet%205-c96442)

[English](README.md) · Deutsch

Ein Lotse bringt Schiffe sicher durch schwieriges Fahrwasser. Nachtlotse
macht das Gleiche für deine Beobachtungsnacht und beantwortet eine Frage:
Was fotografiere ich heute Nacht?

Du sagst dem Programm, wo du stehst und mit welcher Ausrüstung. Es rechnet
den Himmel über deinem Standort für diese Nacht durch und gibt dir eine
kurze Liste mit Zielen, jedes mit einer Bewertung (GO, MARGINAL oder SKIP)
und der Begründung dazu. Dabei zählen dein echter Horizont, das Bildfeld
deiner Kamera, der Mond, die Wettervorhersage und die Frage, wie dunkel die
Nacht überhaupt wird. Außerdem zeigt es Kometen, Supernovae und Novae, die
gerade hell genug sind, und wie ein Ziel in deinen Bildausschnitt passt.

Die ganze Astronomie wird aus den JPL-Ephemeriden berechnet und gegen
bekannte Werte getestet. Geschätzt wird nichts.

<p align="center">
  <img src="screenshots/gui-shortlist.png" alt="Nachtlotse-App: der Reiter Shortlist" width="49%">
  <img src="screenshots/gui-sky-chart.png" alt="Nachtlotse-App: der Reiter Sky chart" width="49%">
</p>

<p align="center"><sub>Derselbe Plan in zwei Ansichten: Volkssternwarte Hochtaunus, TEC AP 160/1120 f/7 FL, die Nacht vom 25. September.</sub></p>

## Dokumentation

Die ausführliche Dokumentation steht im
**[Wiki](https://github.com/beschne/nachtlotse/wiki/Startseite)**, auf
Deutsch und Englisch.

- [Installieren](https://github.com/beschne/nachtlotse/wiki/Installieren) und [Erster Start](https://github.com/beschne/nachtlotse/wiki/Erster-Start)
- [Eine Nacht planen](https://github.com/beschne/nachtlotse/wiki/Eine-Nacht-planen), [Aktuelle Ereignisse](https://github.com/beschne/nachtlotse/wiki/Aktuelle-Ereignisse), [Bildausschnitt](https://github.com/beschne/nachtlotse/wiki/Bildausschnitt), [Bester Himmel](https://github.com/beschne/nachtlotse/wiki/Bester-Himmel)
- [Wie die Rangfolge entsteht](https://github.com/beschne/nachtlotse/wiki/Wie-die-Rangfolge-entsteht) und [Bewertungen](https://github.com/beschne/nachtlotse/wiki/Bewertungen)
- [Befehlsreferenz](https://github.com/beschne/nachtlotse/wiki/Befehlsreferenz)
- [Fehlerbehebung](https://github.com/beschne/nachtlotse/wiki/Fehlerbehebung) und [Fragen und Antworten](https://github.com/beschne/nachtlotse/wiki/Fragen-und-Antworten)

## Schnellstart

Du brauchst macOS und [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/beschne/nachtlotse.git
cd nachtlotse
uv sync
cp nachtlotse/data/sites_local.template.yaml nachtlotse/data/sites_local.yaml
cp nachtlotse/data/rigs_local.template.yaml nachtlotse/data/rigs_local.yaml
# beide Dateien bearbeiten: dein eigener Standort, deine eigene Ausrüstung
uv run lotse plan          # die Liste für heute Nacht auf der Kommandozeile
uv sync --extra gui && uv run lotse gui    # oder die Mac-App
```

## Für Entwickler

Die Quellen der Dokumentation liegen in [`docs/wiki/`](docs/wiki/) und werden
mit `scripts/publish_wiki.py` veröffentlicht. Architektur und Projektregeln
stehen in [CLAUDE.md](./CLAUDE.md), der Stand Modul für Modul in
[STATUS.md](./STATUS.md), die Pläne in [ROADMAP.md](./ROADMAP.md). Diese
Entwicklerdokumente gibt es nur auf Englisch.

```bash
uv run pytest        # Tests (offline, etwa 20 Sekunden)
uv run ruff check .  # Lint
```

## Lizenz

[MIT](./LICENSE)

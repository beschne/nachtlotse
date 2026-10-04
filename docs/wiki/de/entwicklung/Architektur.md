# Architektur

**English:** [Architecture](Architecture)

Nachtlotse ist in Python geschrieben. Der Code ist in Schichten aufgeteilt,
mit einer klaren Regel: Die Engine macht die ganze Astronomie und weiß
nichts von Dateien, Netzwerk oder Bildschirmen.

```
nachtlotse/
├── engine/          # reine Rechnungen, keine Dateien, kein Netzwerk
│   ├── ephemeris.py       # Positionen über skyfield, Kometenpositionen
│   ├── constraints.py     # Dunkelphase, Höhe, Mond, Horizont
│   ├── framing.py         # Bildfeld, Fit, Reach, Bildfeldrotation, Grenzen
│   ├── framing_preview.py # Lage des Bildfelds am Himmel
│   ├── grouping.py        # Ziele, die in ein Bild passen
│   ├── comets.py          # Kometen als Ziele
│   ├── scoring.py         # Bewertungen
│   └── models.py          # Datenklassen: Site, Rig, Target, ...
├── data/            # Katalog, deine Standorte/Rigs/Favoriten
├── weather/         # Open-Meteo
├── events/          # MPC, COBS, Rochester, TNS
├── planning.py      # setzt Engine, Daten, Wetter und Ereignisse zusammen
├── sky_survey.py    # Himmelsbilder für den Bildausschnitt
├── charting.py, chart_export.py, frame_export.py   # Karten und PNG-Dateien
├── best_sky.py      # Standortvergleich
├── prose.py         # freiwilliges Briefing über die Claude-API
├── gui/             # die Mac-App (PySide6)
└── cli.py           # die Kommandozeile
```

Abhängigkeiten zeigen nur in eine Richtung: `cli.py` und `gui/` nutzen
`planning`, das nutzt `engine`, `data`, `weather` und `events`. Die Engine
importiert keines davon. PySide6 wird erst geladen, wenn du die App startest.

Funktionen der Engine sind rein: gleiche Eingabe, gleiche Ausgabe. Werte, die
in einer Nacht für alle Ziele gleich sind (Dunkelphase, Sonnen- und
Mondpositionen), werden einmal berechnet und gemerkt. Deshalb dauert der
ganze Katalog nur etwa 3 Sekunden.

Zeiten sind immer mit Zeitzone versehen und intern in UTC, Ortszeit gibt es
nur auf dem Bildschirm. Zahlen tragen ihre Einheit im Namen
(`focal_length_mm`, `alt_deg`).

Mehr Details, Modul für Modul, stehen in `STATUS.md` im Repository. Die
Regeln des Projekts für Mitwirkende (und für Claude Code) stehen in
`CLAUDE.md`.

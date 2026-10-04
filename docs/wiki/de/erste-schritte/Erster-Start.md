**English:** [First Run](First-Run)

Wenn [Installieren](Installieren) erledigt ist und deine
[Standorte](Standorte-einrichten) und deine
[Ausrüstung](Teleskope-und-Kameras) eingetragen sind:

```bash
uv run lotse sites     # deine Standorte, so wie Nachtlotse sie liest; zuerst prüfen
uv run lotse rigs      # deine Ausrüstung mit Bildfeld und Abbildungsmaßstab
uv run lotse plan      # die Liste für heute Nacht, erster Standort, erste Ausrüstung
```

Beim allerersten Start lädt Nachtlotse die JPL-Ephemeriden `de421.bsp`
(etwa 17 MB) nach `.cache/skyfield/`. Dafür braucht es einmal Internet.
Danach läuft der Planer offline. Nur Wetter, aktuelle Ereignisse und
Himmelsbilder brauchen eine Verbindung, siehe
[Offline und Zwischenspeicher](Offline-und-Zwischenspeicher).

## Installation prüfen

```bash
uv run pytest
```

Die Tests prüfen die Engine gegen bekannte astronomische Werte. Sie lesen
deine eigenen Standort- und Ausrüstungsdateien nicht und gehen nie ins
Internet. Sie laufen also so oder so durch.

## Nützliche Optionen für den Anfang

```bash
uv run lotse plan --site "Großer Feldberg" --rig S30P   # anderer Standort, andere Ausrüstung
uv run lotse plan --date 2026-11-14     # eine andere Nacht
uv run lotse plan --limit 0             # den ganzen Katalog prüfen
uv run lotse plan --type galaxy         # nur eine Objektart (mehrfach möglich)
uv run lotse events                     # Kometen, Supernovae, Novae heute Nacht
uv run lotse best-sky --radius-km 50    # welcher Standort ist am klarsten
```

`--site` und `--rig` nehmen einen Namen, einen Alias oder einen eindeutigen
Teil davon.

## Die App

```bash
uv sync --extra gui    # einmal
uv run lotse gui
```

Die App rechnet mit derselben Engine und deinen Standorten und deiner
Ausrüstung. Demodaten gibt es nicht. Wenn eine Tabelle leer ist, ist nichts
am Himmel. Weiter mit [Eine Nacht planen](Eine-Nacht-planen).

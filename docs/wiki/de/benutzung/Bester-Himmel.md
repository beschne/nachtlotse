**English:** [Best Sky](Best-Sky)

Best Sky beantwortet eine andere Frage: nicht was, sondern wo. Der Befehl
vergleicht die Wolkenvorhersage deiner eingetragenen Standorte, jeweils für
deren eigene Dunkelphase.

```bash
uv run lotse best-sky
uv run lotse best-sky --site Feldberg --radius-km 50 --date 2026-11-14
```

`--site` ist der Bezugsstandort, `--radius-km` behält nur Standorte in dieser
Entfernung davon, und `--date` wählt die Nacht.

## In der App

Der Reiter Best sky hat drei Einstellungen. Center ist der Bezugsstandort,
Radius begrenzt die Entfernung (Vorgabe 50 km, 0 heißt alle Standorte), und
die Regions-Häkchen filtern das Ergebnis, ohne neu zu laden. Beim ersten
Öffnen aktualisiert sich der Reiter selbst. Danach drückst du Refresh, wenn
du Center oder Radius änderst.

Jede Zeile zeigt Standort, Region, Entfernung und Richtung, die Bewölkung
(„Clouds up to“ mit Mittelwert) und einen kleinen Balken mit einer Zelle pro
Stunde. Alle Zeilen nutzen dieselbe Stundenachse, eine kürzere Nacht zeigt
sich also als leere Zellen am Rand. Plan this site stellt den Standort links
ein und wechselt zurück zur Shortlist.

Ein Standort ohne Daten zeigt entweder „Weather unavailable“ (die Vorhersage
ließ sich nicht abrufen) oder „Beyond forecast range“ (das Datum liegt mehr
als 16 Tage in der Zukunft).

Best Sky hängt nicht vom Rig ab. Die Vorhersagen kommen von Open-Meteo, siehe
[Wetter](Wetter).

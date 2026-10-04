# Befehlsreferenz

**English:** [CLI Reference](CLI-Reference)

Alle Befehle beginnen mit `uv run lotse`. `uv run lotse <Befehl> --help`
zeigt dieselben Angaben auf Englisch.

Wo ein Befehl `--site` oder `--rig` nimmt, gehen ein Name, ein Alias oder
ein eindeutiger Teil davon. Ohne die Angabe gelten der erste Standort und
das erste Rig aus deinen Dateien. `--date` ist immer `JJJJ-MM-TT`, in der
Ortszeit des Standorts, und steht ohne Angabe für heute Nacht.

## lotse plan

Sortiert den Katalog für eine Nacht und vergibt Bewertungen. Siehe
[Eine Nacht planen](Eine-Nacht-planen).

| Option | Bedeutung |
|---|---|
| `--site`, `--rig`, `--date` | Standort, Rig und Nacht |
| `--type KATEGORIE` | nur diese Objektart; mehrfach möglich. Kategorien: `emission_nebula`, `reflection_nebula`, `planetary_nebula`, `dark_nebula`, `galaxy`, `galaxy_group`, `open_cluster`, `globular_cluster`, `variable_star` |
| `--limit N` | nur die N hellsten Katalogobjekte prüfen (Vorgabe 50, 0 für alle) |
| `--chart [PFAD]` | die Himmelskarte als PNG schreiben (Vorgabe `nachtlotse-shortlist.png`); braucht `charts` |
| `--no-events` | Kometen, Supernovae und Novae weglassen |
| `--best-rig` | pro Ziel das beste Rig wählen statt eines festen; nicht mit `--rig` oder `--chart` |
| `--prose` | ein geschriebenes Briefing anhängen; braucht `prose` und einen API-Schlüssel |

## lotse events

Listet aktuelle Kometen, Supernovae und Novae: die, die in der Nacht
beobachtbar sind, und alle anderen mit Begründung. Siehe
[Aktuelle Ereignisse](Aktuelle-Ereignisse). Optionen: `--site`, `--rig`,
`--date`.

## lotse frame ZIEL...

Zeigt, wie ein oder mehrere Ziele in das Bildfeld des Rigs passen. Ein Ziel
kann eine Katalognummer, ein Alias oder ein Name sein (`M31`, `"NGC 224"`)
oder ein aktuelles Ereignis (`161P`, `"C/2026 A2"`, `2026aaiv`). Siehe
[Bildausschnitt](Bildausschnitt).

| Option | Bedeutung |
|---|---|
| `--site`, `--rig`, `--date` | Standort, Rig und Nacht |
| `--out PFAD` | wohin die PNG-Datei geschrieben wird (Vorgabe `nachtlotse-frame-<Ziel>.png`); braucht `charts` |
| `--no-survey` | kein Himmelsbild laden |

## lotse best-sky

Vergleicht die Wolkenvorhersage deiner Standorte. Siehe [Bester Himmel](Bester-Himmel).

| Option | Bedeutung |
|---|---|
| `--site` | Bezugsstandort |
| `--radius-km KM` | nur Standorte innerhalb dieser Entfernung |
| `--date` | Nacht |

## lotse sites, lotse rigs

Listen deine Standorte und Rigs so auf, wie Nachtlotse sie liest. Bei den
Rigs stehen Bildfeld, Abbildungsmaßstab und eine grobe Grenzgröße dabei.

## lotse gui

Startet die Mac-App. Braucht den Zusatz `gui`.

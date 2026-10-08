**English:** [Planning a Night](Planning-a-Night)

```bash
uv run lotse plan                                  # heute Nacht, erster Standort, erstes Rig
uv run lotse plan --site Feldberg --rig S30P --date 2026-11-14
```

In der App wählst du links Standort (SITE), Rig und Datum und drückst
Re-plan.

## Was du bekommst

Oben stehen die Dunkelphase (vom Ende der Abenddämmerung bis zum Beginn der
Morgendämmerung, siehe [Dunkelphase](Dunkelphase)), Mondphase und Mondauf-
oder -untergang sowie die Wettervorhersage für diese Zeit mit einem
stundenweisen Wolkenbalken. Unter dem Wolkenbalken steht die Bewertung der
Nacht, eine Zeile, die sagt, ob sich der Aufbau überhaupt lohnt und was
gegebenenfalls Zeit gekostet hat. Das erklärt [Bewertungen](Bewertungen).

Darunter folgt die Shortlist: die fünf besten Ziele der Nacht, jedes mit
Bewertung (GO, MARGINAL oder SKIP) und Begründung. Wie die Bewertung
zustande kommt, steht in [Bewertungen](Bewertungen). Deine
[Favoriten](Favoriten) kommen hinter den ersten fünf dazu, wenn sie sichtbar
sind.

Danach kommt die vollständige Rangliste mit allem, was in der Nacht
beobachtbar ist. Die Spalten:

| Spalte | Bedeutung |
|---|---|
| Alt, Az | Höhe und Richtung zur besten Zeit |
| Fit | wie gut das Ziel dein Bildfeld füllt, 0 bis 1 |
| Reach | wie gut sich seine Flächenhelligkeit von deinem Himmel abhebt, 0 bis 1 |
| Best | die beste Zeit für die Aufnahme (der höchste Moment, der alle Grenzen einhält) |

Fit und Reach erklärt [Wie die Rangfolge entsteht](Wie-die-Rangfolge-entsteht).
In der App zeigen die Reiter Shortlist und All ranked dieselben Tabellen.
Fährst du mit der Maus über eine Zeile, siehst du die Begründung der
Bewertung.

Am Ende stehen Kometen, Supernovae und Novae, siehe
[Aktuelle Ereignisse](Aktuelle-Ereignisse).

## Gruppen

Ziele, die nah genug beieinander stehen, um in ein Bild deines Rigs zu
passen, etwa M81 und M82, erscheinen als ein Eintrag mit beiden Namen. Dafür
musst du nichts einstellen.

## Nützliche Optionen

`--date JJJJ-MM-TT` plant eine andere Nacht. Wetter gibt es nur bis 16 Tage
im Voraus, der Rest des Plans funktioniert für jedes Datum.

`--type galaxy` beschränkt die Liste auf eine Objektart. Mehrfach möglich:
`--type galaxy --type globular_cluster`.

`--limit N` prüft nur die N hellsten Katalogobjekte (Vorgabe 50,
`--limit 0` für alle 236). Der ganze Katalog braucht etwa 3 Sekunden. In der
App ist das das Feld EVALUATE.

`--best-rig` probiert für jedes Ziel alle eingetragenen Rigs und behält das,
bei dem es am besten ins Bild passt. Jede Zeile nennt dann ihr Rig. Die
Option lässt sich nicht mit `--rig`, `--chart` oder `--skylist` kombinieren und bildet
keine Gruppen.

`--chart`, `--skylist` und `--prose` stehen in [Himmelskarte und Export](Himmelskarte-und-Export)
und [Nachtbriefing](Nachtbriefing). Alle Optionen findest du in der
[Befehlsreferenz](Befehlsreferenz).

## Ein Ziel ins Bild setzen

Wie ein Ziel aus der Liste in dein Bildfeld passt, zeigt `lotse frame` oder
in der App ein Doppelklick auf die Zeile. Siehe [Bildausschnitt](Bildausschnitt).

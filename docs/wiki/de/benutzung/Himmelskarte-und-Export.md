**English:** [Sky Chart and Exports](Sky-Chart-and-Exports)

## Die Himmelskarte

Der Reiter Sky chart zeigt die Shortlist auf einer runden Himmelskarte. Die
Mitte ist der Zenit, der Rand der Horizont, Norden ist oben. Die graue
Fläche ist der Teil des Himmels, den dein Horizont verdeckt.

Jedes Ziel ist als seine Bahn durch die Nacht gezeichnet, eingefärbt nach
seiner Bewertung. Ein Punkt markiert die beste Zeit, in einer eigenen Farbe,
damit du die Ziele in der Legende auseinanderhalten kannst. Favoriten
bekommen statt des Punkts einen Stern. Der Mond hat eine eigene Bahn und ein
kleines Symbol mit seiner Phase.

Mit `-`, `+` und Fit zoomst du die Karte.

![Die Himmelskarte](https://raw.githubusercontent.com/wiki/beschne/nachtlotse/images/gui-sky-chart.png)

Auf der Kommandozeile schreibt `lotse plan --chart` die Karte als PNG
(`nachtlotse-shortlist.png` im aktuellen Ordner oder ein Pfad deiner Wahl).
Dafür brauchst du den Zusatz `charts`.

## Export aus der App

Jede Ansicht der App hat einen Export-Knopf:

| Ansicht | Export |
|---|---|
| Shortlist, All ranked | CSV |
| Sky chart | PNG |
| Briefing | Textdatei |
| Sites, Rigs | Textdatei |
| Bildausschnitt | PNG |

Der Speichern-Dialog startet im Ordner `exports/` des Repositorys.

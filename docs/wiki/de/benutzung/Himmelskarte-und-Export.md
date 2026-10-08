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
| Shortlist, All ranked | CSV, SkySafari-Liste |
| Events | SkySafari-Liste |
| Sky chart | PNG |
| Briefing | Textdatei |
| Sites, Rigs | Textdatei |
| Bildausschnitt | PNG |

Der Speichern-Dialog startet im Ordner `exports/` des Repositorys.

## SkySafari-Listen

Der SkySafari-Export schreibt eine Beobachtungsliste (`.skylist`), die du in
SkySafari auf Handy oder Tablet öffnest. So hast du die Ziele der Nacht am
Teleskop zur Hand. In der App nutzt du dafür Export SkySafari im Reiter
Shortlist, All ranked oder Events. Auf der Kommandozeile schreibt
`lotse plan --skylist` die Liste (`nachtlotse.skylist` im aktuellen Ordner
oder ein Pfad deiner Wahl).

Das steht in der Liste:

- Shortlist: die Ziele der Shortlist, danach die Kometen, Supernovae und
  Novae, die in der Nacht beobachtbar sind. Mit `--skylist-scope ranked`
  schreibt der Befehl statt der Shortlist die ganze Rangliste.
- All ranked: alle Ziele der Rangliste, danach dieselben Ereignisse.
- Events: nur die Ereignisse, die in der Nacht beobachtbar sind.

Katalogobjekte und Kometen öffnen sich in SkySafari wie jedes andere
Objekt. Messier- und NGC-Objekte findet SkySafari über Name und
Katalognummer, Kometen über den Namen.

Supernovae und Novae stehen nicht in den Katalogen von SkySafari, und
SkySafari kann keine eigenen Objekte anlegen. Sie erscheinen grau in der
Liste und lassen sich nicht auswählen. Damit du trotzdem weißt, wohin du
zielen musst, stehen ihre J2000-Koordinaten im Namen, zum Beispiel
`SN 2026abc (RA 12h34m Dec +12d30m J2000)`.

Geprüft wurde das mit SkySafari 6.

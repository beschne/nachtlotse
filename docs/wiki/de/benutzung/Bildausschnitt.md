# Bildausschnitt

**English:** [Framing Preview](Framing-Preview)

Die Vorschau zeigt, wie ein Ziel zu seiner besten Zeit in der Nacht in deinem
Kamerabild liegt.

```bash
uv run lotse frame M31
uv run lotse frame M81 M82 --rig S30P --date 2026-11-14
uv run lotse frame "NGC 7000" --no-survey     # ohne Himmelsbild
```

In der App doppelklickst du auf eine Zeile in Shortlist, All ranked oder
Events, oder du wählst sie aus und drückst Framing preview….

![Das Fenster mit dem Bildausschnitt](https://raw.githubusercontent.com/wiki/beschne/nachtlotse/images/gui-framing.png)

## Was du siehst

Das gelbe Rechteck ist dein Bildfeld, berechnet aus Brennweite und Sensor.
Um das Ziel zeigt der gestrichelte Kreis seine Größe laut Katalog. Für
längliche Objekte kennt der Katalog keine Ausrichtung. Der Kreis zeigt also,
wie weit das Objekt reicht, nicht seine Form. Andere Katalogobjekte im
Bildfeld sind ebenfalls eingezeichnet.

Dahinter liegt ein echtes Himmelsbild (DSS2 in Farbe vom CDS-Bilddienst),
wenn du online bist. Norden ist oben, Osten links.

## Auf einer Alt-Az-Montierung

Eine Alt-Az-Montierung hält die Kamera waagerecht zum Horizont. Die
Oberkante des Bildfelds zeigt zum Zenit. Deshalb steht das Bildfeld schräg
zur Nordrichtung und dreht sich im Lauf der Nacht weiter. Der kleine Pfeil
zeigt die Richtung zum Zenit zu der Uhrzeit, die im Titel steht.

Der Ring aus Strichen um das Bildfeld zeigt, wohin die Oberkante zu jeder
vollen Stunde der Dunkelphase zeigt, solange das Ziel höher als 20° steht.
Stunden, die dicht beieinander liegen, teilen sich eine Beschriftung, etwa
„23–02“. So siehst du auf einen Blick, wie stark sich das Bildfeld während
deiner Aufnahme dreht. Siehe [Bildfeldrotation](Bildfeldrotation).

Auf einer EQ-Montierung dreht sich das Bildfeld nicht. Es wird mit der
langen Seite in Ost-West-Richtung gezeichnet.

## Mehrere Ziele

Nennst du mehrere Ziele, landen sie zusammen in einem Bild, zum Beispiel
`lotse frame M81 M82`. Sie müssen in ein Bildfeld passen.

## Ausgabedateien

`lotse frame` gibt die Zahlen aus und schreibt eine PNG-Datei
`nachtlotse-frame-<Ziel>.png` in den aktuellen Ordner, etwa
`nachtlotse-frame-M81+M82.png`. Eine vorhandene Datei mit diesem Namen wird
überschrieben. Mit `--out` wählst du einen anderen Pfad. Für PNG brauchst du
den Zusatz `charts`. In der App schreibt Export PNG… dasselbe Bild.

Himmelsbilder landen in `.cache/sky_survey/` und laufen nie ab. Ohne
Internet und ohne gespeichertes Bild wird die Vorschau ohne Bild gezeichnet.

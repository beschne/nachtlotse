# Der Katalog

**English:** [The Catalog](The-Catalog)

Nachtlotse bringt einen ausgewählten Katalog mit 236 Deep-Sky-Objekten mit:
63 Messier-Objekte und 173 weitere bekannte Fotoziele aus NGC, IC,
Sharpless, Abell, van den Bergh und Caldwell.

| Art | Anzahl |
|---|---|
| Galaxien | 87 |
| Emissionsnebel | 58 |
| offene Sternhaufen | 38 |
| planetarische Nebel | 30 |
| Reflexionsnebel | 28 |
| Galaxiengruppen | 20 |
| Dunkelnebel | 9 |
| Kugelsternhaufen | 8 |
| veränderliche Sterne | 1 (T CrB) |

Manche Objekte zählen zu mehreren Arten (M42 ist Emissions- und
Reflexionsnebel), deshalb ergibt die Summe mehr als 236.

## Woher die Daten stammen

Die Liste begann mit dem Messier-Katalog und wurde um die Ziele aus Ruben
Kiers „The 100 Best Astrophotography Targets“ sowie aus Charles Brackens
„The Astrophotography Planner“ und „The Astrophotography Sky Atlas“
erweitert. Koordinaten, Größen und Helligkeiten wurden gegen OpenNGC
geprüft, und gegen SIMBAD und NED, wo OpenNGC nichts hatte.

Jedes Objekt steht nur einmal im Katalog. Andere Bezeichnungen landen in
`aliases`, M31 findest du also auch als NGC 224. Die Koordinaten beziehen
sich auf J2000 und sind auf etwa eine Bogenminute genau. Für die Planung
reicht das, zum Ausrichten eines Teleskops nicht.

## Unbekanntes bleibt unbekannt

Für 46 Objekte gibt es keine verlässliche Gesamthelligkeit, meist große,
lichtschwache Emissions- und Dunkelnebel. Sie stehen ohne Helligkeit im
Katalog statt mit einer erfundenen. Objekte, für die sich weder eine
Helligkeit noch eine verlässliche Größe finden ließ, fehlen ganz. Welche das
sind und warum, steht in `SKIPPED-OBJECTS.md` im Repository.

Für längliche Objekte kennt der Katalog keine Ausrichtung (Positionswinkel).
Der [Bildausschnitt](Bildausschnitt) zeichnet ihre Größe deshalb als Kreis.

## Die Dateien

Der Katalog liegt in `nachtlotse/data/catalog/` als YAML-Dateien, nach
Helligkeit sortiert (`mag_lt_6.yaml` bis `mag_15_16.yaml`, dazu
`mag_unknown.yaml`). Nachtlotse lädt die hellsten zuerst. Deshalb fallen bei
einem kleinen `--limit` die lichtschwächsten Objekte zuerst weg.

Deine eigenen Favoriten stehen nicht hier, sondern in einer lokalen Datei,
siehe [Favoriten](Favoriten).

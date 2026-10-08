**English:** [Weather](Weather)

Das Wetter kommt von Open-Meteo, einem kostenlosen Vorhersagedienst ohne
Konto und Schlüssel. Nachtlotse holt die stündliche Vorhersage für den
Standort und schaut auf die Stunden innerhalb der Dunkelphase.

Es nutzt vier Werte:

- Bewölkung, höchste und mittlere,
- Wind, stärkster,
- den kleinsten Abstand zwischen Temperatur und Taupunkt (Taugefahr).

Sie gehen in die [Bewertungen](Bewertungen) ein. Im Kopf der Ausgabe steht
außerdem die Bewölkung Stunde für Stunde: als Reihe kleiner Balken auf der
Kommandozeile, als farbige Zellen in der App.

## Dünne hohe Wolken

Open-Meteo teilt die Bewölkung außerdem in eine tiefe, eine mittlere und eine
hohe Schicht. Hohe Wolken (Cirren) sind dünn und lassen oft noch viel Licht
durch. Für die Bewertung der Nacht zählt eine Stunde deshalb mit dem
größten dieser Werte: tiefe Schicht, mittlere Schicht und die Hälfte der
hohen Schicht. Mehr als die Gesamtbewölkung wird es nie. Hat die Vorhersage
für eine Stunde keine Schichten, gilt die Gesamtbewölkung.

Diese „effektive Bewölkung“ nutzt die [Bewertung der Nacht](Bewertungen), um
klare Stunden zu finden, und „Held back by“ zählt damit. Die Bewölkung im Kopf
der Ausgabe und die Regeln für die einzelnen Ziele rechnen weiter mit der
Gesamtbewölkung.

## Grenzen

Die Vorhersage reicht 16 Tage weit. Für eine Nacht danach funktioniert der
Plan trotzdem, nur ohne Wetter, und die Bewertung kommt nicht über MARGINAL
hinaus.

Ohne Internet passiert dasselbe: „Weather unavailable“, die Rangfolge
funktioniert weiter, und die Bewertung sagt, dass ein klarer Himmel nicht
bestätigt werden konnte.

Vorhersagen werden pro Standort eine Stunde lang gespeichert. Planst du
innerhalb dieser Stunde noch einmal, wird nichts neu geladen.
[Bester Himmel](Bester-Himmel) nutzt dieselben Vorhersagen, um deine
Standorte zu vergleichen.

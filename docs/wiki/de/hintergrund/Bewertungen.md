**English:** [Verdicts](Verdicts)

Jedes Ziel auf der Shortlist bekommt eine Bewertung: GO, MARGINAL oder SKIP.
Die Punktzahl bestimmt die Reihenfolge, die Bewertung sagt, ob sich die
Nacht für dieses Ziel lohnt.

Jede Bewertung beginnt bei GO. Jede der folgenden Regeln kann sie
herabsetzen, die schlechteste gewinnt. Jede Regel, die greift, nennt ihren
Grund, du siehst also immer, warum.

| Bedingung | Bewertung | angezeigter Grund |
|---|---|---|
| Bewölkung erreicht 80 % oder mehr | SKIP | „cloud cover up to …%“ |
| Bewölkung erreicht 40 % oder mehr | MARGINAL | „cloud cover up to …%“ |
| Wind erreicht 40 km/h oder mehr | SKIP | „wind up to … km/h“ |
| Wind erreicht 25 km/h oder mehr | MARGINAL | „wind up to … km/h“ |
| Temperatur nur 2 °C oder weniger über dem Taupunkt | MARGINAL | „dew risk“ |
| Ziel bleibt unter 40° Höhe | MARGINAL | „target only reaches …° altitude“ |
| keine Wettervorhersage verfügbar | MARGINAL | „no weather forecast available“ |
| keine astronomische Dunkelheit in dieser Nacht | MARGINAL | „nautical twilight only“ |

Für das Wetter zählen die schlechtesten Werte während der Dunkelphase: die
höchste Bewölkung, der stärkste Wind, der kleinste Abstand zwischen
Temperatur und Taupunkt. Siehe [Wetter](Wetter).

GO heißt also: Die Vorhersage wurde geprüft und ist klar, ruhig und trocken,
und das Ziel steht hoch. Ohne Vorhersage siehst du nie GO, weil Nachtlotse
einen klaren Himmel dann nicht bestätigen kann.

Die Schwellen sind Startwerte, keine Physik. Sie stehen in
`nachtlotse/engine/scoring.py` und lassen sich dort anpassen.

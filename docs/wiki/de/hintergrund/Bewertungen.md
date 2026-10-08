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
| die beste Zeit des Ziels liegt in einer Stunde mit 40 % effektiver Bewölkung oder mehr | MARGINAL | „best time falls in a cloudy hour“ |

Für das Wetter zählen die schlechtesten Werte während der Dunkelphase: die
höchste Bewölkung, der stärkste Wind, der kleinste Abstand zwischen
Temperatur und Taupunkt. Siehe [Wetter](Wetter).

Die letzte Regel schaut auf die Stunde der besten Zeit des Ziels. Hat die Nacht
irgendwo Wolken, diese Stunde ist aber klar, behält das Ziel das MARGINAL aus
der schlechtesten Stunde des Fensters und bekommt den Hinweis „best time falls
in a clear hour“. „Effektive Bewölkung“ zählt dünne hohe Wolken nur halb, siehe
[Wetter](Wetter).

GO heißt also: Die Vorhersage wurde geprüft und ist klar, ruhig und trocken,
und das Ziel steht hoch. Ohne Vorhersage siehst du nie GO, weil Nachtlotse
einen klaren Himmel dann nicht bestätigen kann.

Die Schwellen sind Startwerte, keine Physik. Sie stehen in
`nachtlotse/engine/scoring.py` und lassen sich dort anpassen.

## Die Bewertung der Nacht

Über der Shortlist beantwortet eine Zeile eine andere Frage: Lohnt es sich
überhaupt, heute Nacht aufzubauen? Dafür schaut Nachtlotse in die stündliche
Vorhersage und sucht die längste ununterbrochene Phase mit klaren Stunden in
der Dunkelphase. Eine Stunde gilt als klar, wenn die Bewölkung unter 40 %
liegt. Ein Durchschnitt würde den Verlauf der Nacht verstecken, denn 40 % im
Mittel können heißen: klar bis 01:00 Uhr, danach zu.

| Längste klare Phase | Bewertung der Nacht |
|---|---|
| 3 Stunden oder mehr | GO |
| 1,5 Stunden oder mehr | MARGINAL |
| weniger als 1,5 Stunden | SKIP |

So sieht die Zeile aus:

```
Night verdict: GO — clear 21:30–03:10 (5.7 h)
Night verdict: SKIP — longest clear run 1.0 h from 22:00, GO needs 3 h
```

Eine zweite Zeile, "Held back by", nennt, was die Nacht Zeit gekostet hat,
das Teuerste zuerst: Bewölkung von 40 % oder mehr, Wind ab 25 km/h, eine
Temperatur höchstens 2°C über dem Taupunkt und der Mond, wenn er zu
mindestens 50 % beleuchtet und über dem Horizont ist. Dazu steht jeweils, wie
viele Stunden es betrifft. Das erklärt die Nacht nur. Die Stufe richtet sich
allein nach der klaren Phase.

Ohne Vorhersage steht in der Zeile "unknown". Das passiert auch, wenn die
Vorhersage nur einen Teil der Dunkelphase abdeckt und dieser Teil zu bewölkt
ist, um den Rest zu beurteilen. Auf eine kurze klare Phase dort könnte im
Teil, den wir nicht sehen, eine längere folgen.

Die Bewertung der Nacht ersetzt die Bewertung der einzelnen Ziele nicht. Beide
können auseinanderliegen: Eine Nacht kann GO sein, während ein einzelnes Ziel
nur MARGINAL bekommt, weil es tief steht. Die Schwellen stehen in
`nachtlotse/engine/night.py`.

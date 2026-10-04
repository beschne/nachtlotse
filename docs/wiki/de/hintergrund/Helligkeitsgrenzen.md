**English:** [Brightness Limits](Brightness-Limits)

Nachtlotse schätzt, wie lichtschwache Objekte dein Rig an einem Standort
noch erreicht. Diese grobe Grenzgröße zeigt `lotse rigs`, und sie
entscheidet, welche Kometen, Supernovae und Novae als beobachtbar gelten.

## Die Schätzung

Ausgangspunkt ist die klassische Faustregel für visuelle Teleskope,
2,7 + 5 × log10 der Öffnung in mm. Dazu kommen 7 Größenklassen für das, was
gestapelte Langzeitbelichtungen gegenüber dem Auge gewinnen, und eine
Korrektur für die Himmelshelligkeit deines Standorts (aus seiner
Bortle-Klasse).

Für das Seestar S30 Pro (30 mm) bei Bortle 5 ergibt das etwa 16,0. Die 7
Größenklassen fürs Stacking sind die größte Unsicherheit: Eine viel längere
oder kürzere Aufnahme verschiebt die echte Grenze. Der Wert steht in
`nachtlotse/engine/framing.py` und lässt sich anpassen.

## Für aktuelle Ereignisse

Ereignisse müssen etwas heller sein als die Grenze:

| Art | Abstand | Seestar S30 Pro bei Bortle 5 |
|---|---|---|
| Kometen | 2 mag (ihr Licht ist verteilt) | bis 14,0 |
| Supernovae, Novae | 1 mag (Lichtpunkte) | bis 15,0 |

Ein Standort ohne Bortle-Klasse bekommt keine Grenze. Nachtlotse rät die
Himmelshelligkeit nicht.

Katalogobjekte werden mit dieser Grenze nicht gefiltert. Bei ihnen übernimmt
die „Reach“ in der Punktzahl diese Aufgabe, siehe
[Wie die Rangfolge entsteht](Wie-die-Rangfolge-entsteht).

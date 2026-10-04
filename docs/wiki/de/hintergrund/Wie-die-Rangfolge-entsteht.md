**English:** [How Ranking Works](How-Ranking-Works)

Nachtlotse sortiert in drei Schritten: für jedes Ziel die beste Zeit finden,
es bewerten, dann sortieren.

## 1. Die beste Zeit

Die Dunkelphase der Nacht (siehe [Dunkelphase](Dunkelphase)) wird an 25
gleichmäßig verteilten Zeitpunkten geprüft. Zu jedem Zeitpunkt gilt ein Ziel
als beobachtbar, wenn alles das zutrifft:

- es steht mindestens 20° über dem Horizont,
- es steht in seiner Richtung über deiner eigenen Horizontlinie (siehe [Standorte einrichten](Standorte-einrichten)),
- es ist mindestens 30° vom Mond entfernt,
- auf einer Alt-Az-Montierung dreht sich das Bildfeld dort nicht schneller
  als 1,5° pro Minute (siehe [Bildfeldrotation](Bildfeldrotation)).

Die beste Zeit ist der höchste dieser Zeitpunkte. Ein Ziel ohne einen
solchen Zeitpunkt taucht im Plan gar nicht auf.

## 2. Die Punktzahl

Die Punktzahl ist das Produkt aus drei Werten zwischen 0 und 1:

Punktzahl = (Höhe ÷ 90°) × Fit × Reach

Weil multipliziert wird, drückt ein sehr schlechter Wert die Punktzahl nach
unten, egal wie gut die anderen beiden sind.

Fit sagt, wie gut das Ziel dein Bildfeld füllt. Die größte Ausdehnung des
Ziels wird mit der kurzen Seite deines Bildfelds verglichen. Ein Ziel genau
dieser Größe bekommt 1,0. Kleinere Ziele bekommen entsprechend weniger, ein
Ziel, das ein Viertel füllt, also 0,25. Ein Ziel, das größer ist als das
Bildfeld, verliert wieder, weil es abgeschnitten wird. Ist die Größe
unbekannt, ist Fit 1,0.

Reach sagt, ob sich das Licht des Ziels von deinem Himmel abhebt. Nachtlotse
verteilt die Gesamthelligkeit des Ziels auf seine Fläche, das ergibt seine
Flächenhelligkeit. Die vergleicht es mit der Himmelshelligkeit deines
Standorts (einem SQM-Wert, wenn du einen eingetragen hast, sonst einer
Schätzung aus der Bortle-Klasse) plus 3 Größenklassen für das, was Stacking
herausholt. Ist das Ziel heller, bekommt es 1,0. Ist es lichtschwächer,
verliert es über die nächsten 3 Größenklassen an Reach, bis hinunter auf
0,2. Ganz aus der Liste fällt es dadurch nie, denn die Schätzung ist nicht
exakt. Fehlen Helligkeit, Größe oder Himmelshelligkeit, ist Reach 1,0.

## 3. Sortieren und die Shortlist

Alle beobachtbaren Ziele werden nach Punktzahl sortiert. Die ersten fünf
bilden die Shortlist, sichtbare [Favoriten](Favoriten) kommen dahinter.

## Gruppen

Ziele, die nah genug beieinander stehen, werden zu einem Eintrag
zusammengefasst. Zwei Ziele passen zusammen, wenn ihr Abstand nicht größer
ist als die kurze Seite deines Bildfelds. Bei einer Gruppe berechnet sich
Fit aus dem Abstand der Mitglieder, und die beste Zeit ist der beste Moment,
in dem alle gleichzeitig beobachtbar sind.

## Wie viel geprüft wird

Ohne weitere Angabe prüft Nachtlotse nur die 50 hellsten Katalogobjekte
(`--limit`, EVALUATE in der App). Der Katalog ist nach Helligkeit sortiert,
eine kleinere Zahl lässt also zuerst die lichtschwächsten Objekte weg.
Favoriten werden immer geprüft. Mit `--limit 0` wird der ganze Katalog mit
236 Objekten geprüft, das dauert etwa 3 Sekunden.

Die Bewertung (GO, MARGINAL, SKIP) ist von der Punktzahl getrennt, siehe
[Bewertungen](Bewertungen).

# Fragen und Antworten

**English:** [FAQ](FAQ)

**Warum sehe ich fast nie GO?**
Für GO braucht es eine Vorhersage, die klar, ruhig und trocken ist, und ein
Ziel über 40°. Ohne Vorhersage kann Nachtlotse keinen klaren Himmel
bestätigen und bleibt bei MARGINAL. Siehe [Bewertungen](Bewertungen).

**Warum landet ein kleines Objekt mit meinem Weitwinkel-Rig weit hinten?**
Weil es nur einen kleinen Teil des Bildfelds füllen würde. Das ist der „Fit“
in der Punktzahl, siehe [Wie die Rangfolge entsteht](Wie-die-Rangfolge-entsteht).
Mit längerer Brennweite rückt es nach vorn.

**Mein Favorit fehlt.**
Dann ist er in dieser Nacht nicht sichtbar: zu tief, hinter deinem Horizont,
zu nah am Mond oder (bei Alt-Az) nur nahe am Zenit.

**Steuert Nachtlotse mein Teleskop?**
Nein. Es plant nur. Ausrichten und Aufnehmen machst du weiter mit deiner
eigenen Software.

**Funktioniert es auf der Südhalbkugel?**
Die Rechnungen sind nicht auf den Norden beschränkt, getestet sind sie
bisher aber nur für Mitteleuropa.

**Kann ich Objekte zum Katalog hinzufügen?**
Ja, in `nachtlotse/data/catalog/`. Jeder Wert muss aus einer echten Quelle
stammen (OpenNGC, SIMBAD, NED), siehe [Der Katalog](Der-Katalog). Für
Objekte, die dir einfach persönlich wichtig sind, nimm lieber die
[Favoriten](Favoriten).

**Warum sagt Nachtlotse die Helligkeit von Kometen nicht voraus?**
Weil die veröffentlichten Formeln nicht zu den Messungen passten, siehe
[Datenquellen](Datenquellen). Gemessene Werte sind ehrlicher.

**Wo liegen meine Einstellungen?**
In `nachtlotse/data/*_local.yaml`. Git ignoriert sie, sie überstehen
Updates und werden nie geteilt.

**Entscheidet die KI irgendetwas?**
Nein. Das freiwillige Briefing formuliert nur um, was die Engine berechnet
hat, siehe [Nachtbriefing](Nachtbriefing).

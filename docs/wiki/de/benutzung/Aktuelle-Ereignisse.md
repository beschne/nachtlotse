# Aktuelle Ereignisse

**English:** [Current Events](Current-Events)

Neben dem festen Katalog schaut Nachtlotse auch darauf, was gerade am Himmel
los ist: Kometen, Supernovae und Novae. Du findest sie am Ende von
`lotse plan`, in einem eigenen Befehl und im Reiter Events der App.

```bash
uv run lotse events                  # alles Aktuelle, mit Begründungen
uv run lotse plan --no-events        # Plan ohne sie (kein Download)
uv run lotse frame 161P              # einen Kometen ins Bild setzen
uv run lotse frame 2026aaiv          # eine Supernova ins Bild setzen
```

## Was zählt

Ein Komet zählt, wenn Beobachter in den letzten 14 Tagen seine Helligkeit
gemeldet haben (Quelle: COBS). Seine Position wird aus seiner Bahn
berechnet, die das Minor Planet Center veröffentlicht. Als Helligkeit gilt
der Median dieser Meldungen.

Eine Supernova oder Nova zählt, wenn sie auf David Bishops Liste der
aktiven hellen Objekte steht („Latest Supernovae“, heller als 17 mag). Die
Liste nennt ihre aktuelle Helligkeit. Neue Novae in unserer Milchstraße
kommen vom IAU Transient Name Server (TNS). Für sie ist meist nur die
Helligkeit bei der Entdeckung bekannt. Sie stehen deshalb mit diesem Datum
in der Liste, aber nicht in der Rangfolge.

Warum nicht einfach die Helligkeit aus dem TNS? Weil das TNS die Helligkeit
bei der Entdeckung festhält. SN 2026aaiv in NGC 7331 wurde bei 17,3 mag
entdeckt und erreichte drei Wochen später etwa 11,5 mag.

## Wie sie bewertet werden

Jedes Ereignis durchläuft dieselben Prüfungen wie ein Katalogobjekt: Es muss
hoch genug steigen, über deinem Horizont stehen, Abstand zum Mond halten und
auf einer Alt-Az-Montierung schnelle [Bildfeldrotation](Bildfeldrotation)
vermeiden. Außerdem muss es für deine Ausrüstung hell genug sein, siehe
[Helligkeitsgrenzen](Helligkeitsgrenzen). Dann bekommt es eine Bewertung wie
alles andere.

Ein Komet wandert. Nachtlotse nimmt seine Position in der Mitte der Nacht und
zeigt, wie schnell er sich bewegt, zum Beispiel „moves 7.3′/h“.

Ereignisse gibt es nur für Nächte, die höchstens 14 Tage von heute entfernt
sind. Eine heute gemessene Helligkeit sagt wenig über eine Nacht in zwei
Monaten.

## Die Liste der übrigen

`lotse events` und die untere Tabelle im Reiter Events zeigen alles, was es
nicht geschafft hat, mit dem Grund: zu lichtschwach für dieses Rig, heute
Nacht nicht beobachtbar, noch nicht klassifiziert, letzte Helligkeitsmeldung
älter als ein Monat oder keine aktuelle Helligkeit bekannt.

Woher die Daten stammen und wie oft sie geholt werden, steht in
[Datenquellen](Datenquellen).

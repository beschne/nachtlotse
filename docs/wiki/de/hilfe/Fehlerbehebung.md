**English:** [Troubleshooting](Troubleshooting)

## Installation

`uv: command not found`: Der Installer hat uv nach `~/.local/bin` gelegt, und
das steht noch nicht im PATH. Öffne ein neues Terminal oder trag
`export PATH="$HOME/.local/bin:$PATH"` in `~/.zshrc` ein.

`Permission denied (publickey)` beim Klonen: Du hast keinen SSH-Schlüssel bei
GitHub. Nimm stattdessen die HTTPS-Adresse.

Der erste Start hängt oder bricht beim Download ab: Das sind die 17 MB
Ephemeriden. Sie brauchen einmal Internet, ein Firmen-Proxy oder eine
Firewall kann sie blockieren. Lösch `.cache/skyfield/` und versuch es über
eine normale Verbindung noch einmal.

## Beim Start

„No sites_local.yaml“ oder „No rigs_local.yaml“: Deine Standort- oder
Rig-Datei fehlt. Die Meldung nennt die Vorlage, die du kopieren musst, siehe
[Standorte einrichten](Standorte-einrichten). Nachtlotse rät nie einen
Standort oder ein Rig.

`lotse gui` beschwert sich über PySide6: `uv sync --extra gui` ausführen. Ein
späteres einfaches `uv sync` entfernt es wieder, siehe [Installieren](Installieren).

„PNG export needs matplotlib“: `uv sync --extra charts` ausführen.

## Beim Planen

„Weather unavailable“: Open-Meteo war nicht erreichbar, zum Beispiel an einem
dunklen Standort ohne Empfang. Die Rangfolge funktioniert trotzdem, nur das
Wetter fehlt. „Beyond forecast range“ heißt, das Datum liegt mehr als 16 Tage
in der Zukunft.

Im Kopf steht „nautical only“: In dieser Nacht gibt es keine astronomische
Dunkelheit, das passiert um die Sommersonnenwende. Siehe [Dunkelphase](Dunkelphase).

„No dark window around …“: Weit im Norden kommt die Sonne im Sommer nicht
12° unter den Horizont. Dann gibt es nichts zu planen.

„Comets unavailable“ oder „Supernovae unavailable“: Die Quelle war nicht
erreichbar, und es war nichts gespeichert. Der Plan selbst ist vollständig,
siehe [Offline und Zwischenspeicher](Offline-und-Zwischenspeicher).

Ein erwartetes Ziel fehlt: Prüf zuerst seine Höhe und deinen Horizont. Es
muss irgendwann in der Dunkelphase mindestens 20° hoch stehen, über deiner
Horizontlinie und mindestens 30° vom Mond entfernt. Prüf auch `--limit`:
Ohne Angabe werden nur die 50 hellsten Objekte geprüft.

## Ältere Versionen

„Planning failed: interpolating from IERS_Auto using predictive values that
are more than 30.0 days old": behoben in Version 3.2.0. Aktualisieren mit
`git pull`.

Abstürze für Daten zwischen Ende Mai und Mitte Juli: behoben in 3.2.1.

## Etwas sieht astronomisch falsch aus

Das ist ein echter Fehler. Führ zuerst `uv run pytest` aus, dann eröffne ein
Issue (oder sag Benno im Verein Bescheid) mit deinem Standorteintrag, dem
Rig, dem Datum und dem, was du erwartet hast. Die Engine soll nachprüfbar
sein.

**English:** [Data Sources](Data-Sources)

| Was | Quelle | Wann es geholt wird |
|---|---|---|
| Positionen von Sonne, Mond und Sternen | JPL-Ephemeriden DE421 über skyfield | einmal, beim ersten Start (etwa 17 MB) |
| Daten zur Erdrotation (IERS) | kommen mit astropy | nie, eine ältere Tabelle reicht für die Planung |
| Wetter | [Open-Meteo](https://open-meteo.com) | höchstens einmal pro Stunde und Standort |
| Himmelsbilder für den Bildausschnitt | DSS2 in Farbe über den Dienst [CDS hips2fits](https://alasky.cds.unistra.fr/hips-image-services/hips2fits) | einmal pro Ziel und Bildfeld |
| Kometenbahnen | [Minor Planet Center](https://www.minorplanetcenter.net), `CometEls.txt` | höchstens einmal am Tag |
| Kometenhelligkeit | [COBS](https://cobs.si), Beobachtermeldungen der letzten 14 Tage | höchstens zweimal am Tag |
| Helligkeit und Position von Supernovae und Novae | David Bishops [Latest Supernovae](https://www.rochesterastronomy.org/supernova.html) | höchstens zweimal am Tag |
| neue Novae, Ersatz für fehlende Positionen | [IAU Transient Name Server](https://www.wis-tns.org), öffentliche Suche | etwa einmal am Tag |
| Text des Nachtbriefings (freiwillig) | Anthropic-API | nur, wenn du es anforderst |

Keine dieser Quellen braucht ein Konto, außer der Anthropic-API für das
Briefing.

## Warum diese Quellen

Bei Kometen nimmt Nachtlotse, was Beobachter tatsächlich gemessen haben. Die
Helligkeitsformel in der MPC-Datei passte nicht zur eigenen Vorhersage des
MPC (10P/Tempel am 4. Oktober 2026: 13 bis 14 mag laut Datei, 9,0 laut
MPC-Vorhersage, 10,2 gemessen), deshalb wird sie gar nicht verwendet. COBS
bietet auch ein Feld „current magnitude“ an. Das ist aber ein Modellwert,
den es für fast jeden je gesehenen Kometen gibt, also wird auch er nicht
verwendet.

Bei Supernovae kennt das TNS nur die Helligkeit bei der Entdeckung. Die
Rochester-Liste führt die zuletzt gemeldete Helligkeit, und genau die zählt
für heute Nacht. Ihre Positionen stimmen mit dem TNS auf eine zehntel
Bogensekunde überein.

## Ein guter Gast sein

Alle Quellen sind kostenlose Dienste von Leuten, die uns nichts schulden.
Nachtlotse speichert alles zwischen (siehe
[Offline und Zwischenspeicher](Offline-und-Zwischenspeicher)), fragt so
wenig wie möglich und lässt eine Quelle nach einer fehlgeschlagenen Anfrage
eine Stunde in Ruhe, oder genau so lange, wie der Server es verlangt. Das
TNS erlaubt ohne Konto 10 Anfragen pro Minute.

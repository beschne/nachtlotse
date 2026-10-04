# Offline und Zwischenspeicher

**English:** [Offline and Caching](Offline-and-Caching)

Nach dem ersten Start funktioniert der Kern von Nachtlotse ohne Internet:
Rangfolge, beste Zeiten, Gruppen, Bildausschnitt und Bewertungen. Das ist
Absicht, denn an dunklen Standorten ist der Empfang selten gut.

Ohne Internet fehlen dir:

- das Wetter (Bewertungen bleiben dann höchstens bei MARGINAL),
- aktuelle Ereignisse, sofern sie nicht schon vorher geladen wurden,
- Himmelsbilder im Bildausschnitt, sofern sie nicht schon vorher geladen wurden.

Dadurch bricht nichts ab. Die Ausgabe sagt, was fehlt.

## Was wo gespeichert wird

| Ordner | Inhalt | Wie lange |
|---|---|---|
| `.cache/skyfield/` | JPL-Ephemeriden | dauerhaft |
| `.cache/open_meteo/` | Wettervorhersagen | 1 Stunde |
| `.cache/sky_survey/` | Himmelsbilder | dauerhaft |
| `.cache/events/` | Kometenbahnen, Novae | 24 Stunden |
| | Helligkeit von Kometen und Supernovae | 12 Stunden |
| | Positionen klassifizierter Supernovae und Novae | dauerhaft |

Ist eine gespeicherte Kopie älter und die Quelle nicht erreichbar, wird die
ältere Kopie genommen und ihr Datum angezeigt. Nach einer fehlgeschlagenen
Anfrage bleibt eine Quelle eine Stunde in Ruhe (oder so lange, wie der
Server es verlangt). Schnelles Neuplanen überlastet sie also nie.

Der Ephemeriden-Ordner gehört zum Repository. Die anderen Ordner entstehen
in dem Ordner, aus dem du `lotse` startest. Startest du es aus dem Ordner
des Repositorys, bleibt alles an einer Stelle. Git ignoriert alle
`.cache`-Ordner, und du kannst sie jederzeit löschen.

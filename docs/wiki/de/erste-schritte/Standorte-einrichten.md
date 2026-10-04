# Standorte einrichten

**English:** [Configuring Sites](Configuring-Sites)

Deine Beobachtungsorte stehen in `nachtlotse/data/sites_local.yaml`. Git
ignoriert diese Datei, sie bleibt also auf deinem Rechner. Fang mit der
Vorlage an:

```bash
cp nachtlotse/data/sites_local.template.yaml nachtlotse/data/sites_local.yaml
```

In der Vorlage stehen zwei echte Standorte im Taunus, die Volkssternwarte
Hochtaunus und der Große Feldberg. Behalte sie, ersetze sie oder ergänze
deine eigenen. Der erste Standort in der Datei gilt immer dann, wenn du kein
`--site` angibst. Setz deinen Hausstandort also nach oben.

## Felder

| Feld | Pflicht | Woher |
|---|---|---|
| `name` | ja | ein Name deiner Wahl |
| `lat_deg`, `lon_deg` | ja | Dezimalgrad, Nord und Ost positiv. Rechtsklick in Apple Karten oder Google Maps, oder das GPS deiner Montierung. Vier Nachkommastellen (etwa 10 m) reichen. |
| `elevation_m` | ja | Höhe über Meer, aus einer topografischen Karte oder vom Handy |
| `tz` | nein | Zeitzone, Vorgabe `Europe/Berlin` |
| `region`, `address` | nein | zur Anzeige; `region` nutzen auch die Regionsfilter in der App |
| `aliases` | nein | Kurznamen, `aliases: ["Feldberg"]` erlaubt `--site Feldberg` |
| `bortle` | nein | Text wie `"5 (urban fringe)"`. Daraus wird die Zahl gelesen (`"3-4"` wird zu 3,5) und für [Helligkeitsgrenzen](Helligkeitsgrenzen) und die „Reach“ in [Wie die Rangfolge entsteht](Wie-die-Rangfolge-entsteht) verwendet. Weglassen, wenn du ihn nicht kennst. |
| `zenith_sky_brightness_mag_arcsec2` | nein | nur, wenn du selbst mit einem SQM nahe Neumond gemessen hast. Ersetzt die Schätzung aus der Bortle-Klasse. |
| `horizon_points` oder `sector` | nein | dein Horizont, siehe unten |

## Der Horizont

Das ist der Teil, der die Bewertungen glaubwürdig macht. Ohne ihn empfiehlt
Nachtlotse dir auch ein Ziel, das genau hinter dem Dach des Nachbarn steht.

`horizon_points` ist eine Liste von Paaren `[Azimut, Höhe]` in Grad: die
niedrigste Höhe, die du in jeder Richtung sehen kannst (0° ist Norden, im
Uhrzeigersinn). Werte dazwischen werden interpoliert. Etwa zwanzig Punkte
rundum reichen gut. Mit einer Neigungsmesser-App und einem Kompass hast du
das in einer halben Stunde.

`sector` ist eine Abkürzung für Orte, an denen nur ein Teil des Himmels frei
ist, etwa ein Balkon: `[Anfang, Ende]` oder `[Anfang, Ende, Mindesthöhe]`, im
Uhrzeigersinn. Alles außerhalb dieses Bogens gilt als verdeckt.

Ohne beide Angaben geht Nachtlotse von freier Sicht rundum aus.

## Beispiel

```yaml
- name: "Volkssternwarte Hochtaunus"
  lat_deg: 50.23709
  lon_deg: 8.55088
  elevation_m: 316.0
  region: "Taunus"
  bortle: "5 (heavily light-polluted, urban fringe)"
  aliases: ["Sternwarte", "Kuppel"]
  horizon_points:
    - [0.0, 19.8]
    - [10.5, 10.5]
    - [31.6, 20.6]
    # etwa zwanzig Punkte rundum
```

Prüf das Ergebnis mit `uv run lotse sites`. Der Reiter Sites in der App zeigt
dieselbe Liste. Du kannst sie nach Region oder nach Entfernung von einem
gewählten Standort sortieren und nach Region filtern. Das hilft, wenn du
sehen willst, wo ein neuer Standort hinpasst.

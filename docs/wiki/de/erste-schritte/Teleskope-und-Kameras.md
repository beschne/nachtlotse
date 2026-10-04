**English:** [Configuring Rigs](Configuring-Rigs)

Ein „Rig“ ist bei Nachtlotse eine Kombination aus Teleskop, Kamera und
Montierung. Deine Rigs stehen in `nachtlotse/data/rigs_local.yaml`, die git
ignoriert. Fang mit der Vorlage an:

```bash
cp nachtlotse/data/rigs_local.template.yaml nachtlotse/data/rigs_local.yaml
```

Das erste Rig in der Datei gilt immer dann, wenn du kein `--rig` angibst. In
der Vorlage stehen schon das ZWO Seestar S30 Pro (auf der eigenen Montierung
und auf einer EQ-Wedge), das Seestar S50 Pro, ein RedCat 51 mit ASI2600MC Duo
und ein TEC 160 FL. Wenn du eines davon hast, behalte es und lösch den Rest.

## Felder

`optics.focal_length_mm` und `optics.aperture_mm` stehen im Datenblatt des
Teleskops. Mit Reducer oder Barlowlinse trägst du die resultierende
Brennweite ein.

`sensor.width_px`, `sensor.height_px` und `sensor.pixel_um` stehen im
Datenblatt der Kamera. Zusammen mit der Brennweite ergeben sie das Bildfeld
und den Abbildungsmaßstab. Daran misst Nachtlotse, ob ein Ziel passt.

`mount.kind` ist `"altaz"` oder `"eq"`. Das ist wichtig: Bei Alt-Az-Rigs
prüft Nachtlotse die [Bildfeldrotation](Bildfeldrotation) nahe dem Zenit,
bei EQ-Rigs ist das nicht nötig. Gemeint ist der Aufbau, nicht die Hardware.
Ein Seestar auf einer eingenordeten Wedge ist `"eq"`. Wenn du dieselbe
Ausrüstung auf beide Arten nutzt, trag sie zweimal mit verschiedenen Aliasen
ein.

`name`, `aliases` und die `name`-Felder darin sind freier Text. Mit den
Aliasen funktioniert `--rig S30P`.

## Beispiel

```yaml
- name: "ZWO Seestar S30 Pro"
  aliases: ["S30P"]
  optics:
    name: "Seestar S30 Pro Optics"
    focal_length_mm: 160.0
    aperture_mm: 30.0
  sensor:
    name: "Sony IMX585"
    width_px: 3840
    height_px: 2160
    pixel_um: 2.9
  mount:
    name: "Seestar S30 Pro Mount"
    kind: "altaz"
```

`uv run lotse rigs` zeigt jedes Rig mit Bildfeld (3,99° × 2,24° beim S30 Pro),
Abbildungsmaßstab und einer groben Grenzgröße für zwei Stufen der
Himmelshelligkeit.

## Mehrere Rigs

`lotse plan --best-rig` probiert für jedes Ziel alle Rigs durch und behält
das, bei dem es am besten ins Bild passt. Siehe [Eine Nacht planen](Eine-Nacht-planen).

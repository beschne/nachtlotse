**Deutsch:** [Teleskope und Kameras](Teleskope-und-Kameras)

A rig is one combination of telescope, camera and mount. Your rigs are in
`nachtlotse/data/rigs_local.yaml`, which git ignores. Start from the template:

```bash
cp nachtlotse/data/rigs_local.template.yaml nachtlotse/data/rigs_local.yaml
```

The first rig in the file is used whenever you don't pass `--rig`. The
template already has entries for the ZWO Seestar S30 Pro (on its own mount
and on an EQ wedge), the Seestar S50 Pro, a RedCat 51 with an ASI2600MC Duo
and a TEC 160 FL. If you own one of those, keep it and delete the rest.

## Fields

`optics.focal_length_mm` and `optics.aperture_mm` come from the telescope's
data sheet. If you use a reducer or a Barlow, enter the resulting focal
length.

`sensor.width_px`, `sensor.height_px` and `sensor.pixel_um` come from the
camera's data sheet. Together with the focal length they give the field of
view and the pixel scale. That is how Nachtlotse judges whether a target
fits.

`mount.kind` is `"altaz"` or `"eq"`. It matters: for alt-az rigs Nachtlotse
checks [Field Rotation](Field-Rotation) near the zenith, for EQ rigs it
doesn't need to. This describes how you set up, not the hardware. A Seestar
on a polar-aligned wedge is `"eq"`. If you use the same equipment both ways,
list it twice with different aliases.

`name`, `aliases` and the `name` fields inside are free text. Aliases are
what make `--rig S30P` work.

## Example

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

`uv run lotse rigs` shows every rig with its field of view (3.99° × 2.24°
for the S30 Pro), its pixel scale and a rough limiting magnitude for two
levels of sky darkness.

## More than one rig

`lotse plan --best-rig` tries every rig for every target and keeps the one
that frames it best. See [Planning a Night](Planning-a-Night).

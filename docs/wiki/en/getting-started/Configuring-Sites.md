**Deutsch:** [Standorte einrichten](Standorte-einrichten)

Your observing sites are in `nachtlotse/data/sites_local.yaml`. Git ignores
this file, so it stays on your machine. Start from the template:

```bash
cp nachtlotse/data/sites_local.template.yaml nachtlotse/data/sites_local.yaml
```

The template contains two real sites in the Taunus, the Volkssternwarte
Hochtaunus and the Großer Feldberg. Keep them, replace them or add your own.
The first site in the file is used whenever you don't pass `--site`, so put
your home site at the top.

## Fields

| Field | Required | Where to get it |
|---|---|---|
| `name` | yes | any name you like |
| `lat_deg`, `lon_deg` | yes | decimal degrees, north and east positive. Right-click in Apple Maps or Google Maps, or read your mount's GPS. Four decimals (about 10 m) is enough. |
| `elevation_m` | yes | a topographic map or your phone |
| `tz` | no | time zone, default `Europe/Berlin` |
| `region`, `address` | no | for display; `region` is also used by the region filters in the app |
| `aliases` | no | short names, `aliases: ["Feldberg"]` lets you type `--site Feldberg` |
| `bortle` | no | text like `"5 (urban fringe)"`. The number is read from it (`"3-4"` becomes 3.5) and used for [Brightness Limits](Brightness-Limits) and the "reach" in [How Ranking Works](How-Ranking-Works). Leave it out if you don't know it. |
| `zenith_sky_brightness_mag_arcsec2` | no | only if you measured it yourself with an SQM meter near new moon. It replaces the Bortle estimate. |
| `horizon_points` or `sector` | no | your local horizon, see below |

## The horizon

This is the part that makes the verdicts trustworthy. Without it Nachtlotse
will recommend a target that sits right behind your neighbor's roof.

`horizon_points` is a list of `[azimuth, altitude]` pairs in degrees: the
lowest altitude you can see in each direction (0° is north, counted
clockwise). Values in between are interpolated. About twenty points around
the horizon work well. A clinometer app on your phone plus a compass will get
you there in half an hour.

`sector` is a shortcut for a site where only part of the sky is open, like a
balcony: `[start, end]` or `[start, end, minimum altitude]`, clockwise.
Everything outside this arc counts as blocked.

Leave out both for a free view all around.

## Example

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
    # about twenty points around the horizon
```

Check the result with `uv run lotse sites`. The Sites tab in the app shows
the same list. You can sort it by region or by distance from a chosen site
and filter it by region, which helps when you want to see where a new site
would fit in.

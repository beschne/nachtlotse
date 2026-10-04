# Brightness Limits

**Deutsch:** [Helligkeitsgrenzen](Helligkeitsgrenzen)

Nachtlotse estimates how faint your rig can go at a site. This rough
limiting magnitude is shown by `lotse rigs` and decides which comets,
supernovae and novae are listed as observable.

## The estimate

It starts from the classic rule for visual telescopes, 2.7 + 5 × log10 of
the aperture in mm. Then it adds 7 magnitudes for what stacking long
exposures gains over the eye and corrects for the sky darkness of your site
(from its Bortle class).

For the Seestar S30 Pro (30 mm) at Bortle 5 this gives about 16.0. The 7
magnitudes for stacking are the biggest uncertainty: a much longer or
shorter session shifts the real limit. The value lives in
`nachtlotse/engine/framing.py` and can be tuned.

## For current events

Events have to be somewhat brighter than the limit:

| Kind | Margin | Seestar S30 Pro at Bortle 5 |
|---|---|---|
| comets | 2 mag (their light is spread out) | up to 14.0 |
| supernovae, novae | 1 mag (points of light) | up to 15.0 |

A site without a Bortle class gets no limit. Nachtlotse doesn't guess the
sky darkness.

Catalog objects are not filtered by this limit. For them, the "reach" in the
score does that job, see [How Ranking Works](How-Ranking-Works).

**Deutsch:** [Wetter](Wetter)

Weather comes from Open-Meteo, a free forecast service without an account or
key. Nachtlotse fetches the hourly forecast for the site and looks at the
hours inside the dark window.

It uses four values:

- cloud cover, highest and average,
- wind, highest,
- the smallest gap between temperature and dew point (dew risk).

They feed the [Verdicts](Verdicts). The header also shows the cloud cover
hour by hour: as a row of small bars on the command line, as colored cells in
the app.

## Thin high cloud

Open-Meteo also splits the cloud cover into a low, a middle and a high
layer. High cloud (cirrus) is thin and often still lets a good deal of light
through, so for the night verdict an hour counts with the largest of: the low
layer, the middle layer, and half of the high layer. It never counts for more
than the total cover. If the forecast has no layers for an hour, the total
cover is used.

This "effective cloud" is what the [night verdict](Verdicts) uses to find
clear hours, and what "Held back by" counts. The cloud cover in the header and
the rules for each target still use the total.

## Limits

The forecast reaches 16 days ahead. For a night beyond that, the plan still
works, but there is no weather and the verdict can't be better than
MARGINAL.

Without internet the same happens: "Weather unavailable", the ranking still
works, and the verdict says that clear skies couldn't be confirmed.

Forecasts are cached for one hour per site, so planning again within the hour
doesn't fetch anything. [Best Sky](Best-Sky) uses the same forecasts to
compare your sites.

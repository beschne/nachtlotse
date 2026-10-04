# Best Sky

**Deutsch:** [Bester Himmel](Bester-Himmel)

Best Sky answers a different question: not what to shoot, but where the sky
will be clearest. It compares the cloud forecast of your configured sites,
each for its own dark window.

```bash
uv run lotse best-sky
uv run lotse best-sky --site Feldberg --radius-km 50 --date 2026-11-14
```

`--site` is the reference site, `--radius-km` keeps only sites within that
distance of it, and `--date` picks the night.

## In the app

The Best sky tab has three controls. Center is the reference site, Radius
limits the distance (50 km by default, 0 means all sites) and the Regions
checkboxes filter the results without fetching anything new. The tab
refreshes itself the first time you open it. After that, press Refresh when
you change Center or Radius.

Each row shows the site, its region, distance and direction, the cloud
cover ("Clouds up to" with the average) and a small bar with one cell per
hour. All rows use the same hour axis, so a shorter night shows up as empty
cells at the edges. Plan this site switches the sidebar to that site and
goes back to the Shortlist.

A site without data shows either "Weather unavailable" (the forecast
couldn't be fetched) or "Beyond forecast range" (the date is more than 16
days ahead).

Best Sky doesn't depend on the rig. Forecasts come from Open-Meteo, see
[Weather](Weather).

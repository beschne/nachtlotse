**Deutsch:** [Offline und Zwischenspeicher](Offline-und-Zwischenspeicher)

After the first run, the core of Nachtlotse works without internet: ranking,
best times, groups, framing and verdicts. That's on purpose, dark sites
rarely have good reception.

Without internet you lose:

- the weather (verdicts then stay at MARGINAL at best),
- current events, unless they were fetched earlier,
- sky images in the framing preview, unless they were fetched earlier.

Nothing fails because of this. The output says what is missing.

## What is stored where

| Folder | Content | Kept for |
|---|---|---|
| `.cache/skyfield/` | JPL ephemeris | for good |
| `.cache/open_meteo/` | weather forecasts | 1 hour |
| `.cache/sky_survey/` | sky images | for good |
| `.cache/events/` | comet orbits, novae | 24 hours |
| | comet and supernova brightness | 12 hours |
| | positions of classified supernovae and novae | for good |

When a cached copy is older than that and the source can't be reached, the
older copy is used, with its date shown. After a failed request a source is
left alone for an hour (or as long as the server asks), so a quick re-plan
never hammers it.

The ephemeris folder belongs to the repository. The other folders are
created in the folder you start `lotse` from. Start it from the repository
folder and everything stays in one place. All `.cache` folders are ignored by
git and can be deleted at any time.

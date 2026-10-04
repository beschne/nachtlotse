**Deutsch:** [Datenquellen](Datenquellen)

| What | Source | When it's fetched |
|---|---|---|
| Sun, Moon and star positions | JPL ephemeris DE421, through skyfield | once, on the first run (about 17 MB) |
| Earth rotation data (IERS) | shipped with astropy | never, an old table is fine for planning |
| Weather | [Open-Meteo](https://open-meteo.com) | at most once per hour and site |
| Sky images for the framing preview | DSS2 color through the [CDS hips2fits](https://alasky.cds.unistra.fr/hips-image-services/hips2fits) service | once per target and field of view |
| Comet orbits | [Minor Planet Center](https://www.minorplanetcenter.net), `CometEls.txt` | at most once a day |
| Comet brightness | [COBS](https://cobs.si), observer reports of the last 14 days | at most twice a day |
| Supernova and nova brightness and positions | David Bishop's [Latest Supernovae](https://www.rochesterastronomy.org/supernova.html) | at most twice a day |
| Recent novae, fallback positions | [IAU Transient Name Server](https://www.wis-tns.org), public search | about once a day |
| Nightly briefing text (optional) | Anthropic API | only when you ask for it |

None of these needs an account, except the Anthropic API for the briefing.

## Why these sources

For comets, Nachtlotse uses what observers actually measured. The magnitude
formula in the MPC file didn't match the MPC's own forecast (10P/Tempel on
October 4, 2026: 13 to 14 from the file, 9.0 from the MPC forecast, 10.2
measured), so it isn't used at all. COBS also offers a "current magnitude"
field, but that's a model value that exists for almost every comet ever
seen, so it isn't used either.

For supernovae, TNS knows the brightness only at discovery. The Rochester
list keeps the latest reported brightness, which is what matters for
tonight. Its positions match TNS to a tenth of an arcsecond.

## Being a good guest

All sources are free services run by people who don't owe us anything.
Nachtlotse caches everything (see [Offline and Caching](Offline-and-Caching)),
asks for as little as possible, and after a failed request leaves the source
alone for an hour, or exactly as long as the server asks. TNS allows 10
requests per minute without an account.

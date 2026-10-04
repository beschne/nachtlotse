**Deutsch:** [Bewertungen](Bewertungen)

Every target on the shortlist gets a verdict: GO, MARGINAL or SKIP. The
score decides the order, the verdict says whether the night is worth it for
that target.

Each verdict starts as GO. Every rule below can lower it, and the worst one
wins. Each rule that applies adds its reason, so you always see why.

| Condition | Verdict | Reason shown |
|---|---|---|
| cloud cover reaches 80% or more | SKIP | "cloud cover up to …%" |
| cloud cover reaches 40% or more | MARGINAL | "cloud cover up to …%" |
| wind reaches 40 km/h or more | SKIP | "wind up to … km/h" |
| wind reaches 25 km/h or more | MARGINAL | "wind up to … km/h" |
| temperature only 2°C or less above the dew point | MARGINAL | "dew risk" |
| target stays below 40° altitude | MARGINAL | "target only reaches …° altitude" |
| no weather forecast available | MARGINAL | "no weather forecast available" |
| no astronomical darkness that night | MARGINAL | "nautical twilight only" |

Weather values are the worst ones during the dark window: the highest cloud
cover, the strongest wind, the smallest gap between temperature and dew
point. See [Weather](Weather).

GO therefore means: the forecast was checked and is clear, calm and dry, and
the target is high. Without a forecast you will never see GO, because
Nachtlotse can't confirm the sky is clear.

The thresholds are starting values, not physics. They live in
`nachtlotse/engine/scoring.py` and can be adjusted there.

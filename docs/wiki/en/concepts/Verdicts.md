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
| the target's best time falls in an hour with 40% effective cloud or more | MARGINAL | "best time falls in a cloudy hour" |

Weather values are the worst ones during the dark window: the highest cloud
cover, the strongest wind, the smallest gap between temperature and dew
point. See [Weather](Weather).

The last rule looks at the hour of the target's best time. When the night has
clouds somewhere but that hour is clear, the target keeps the MARGINAL from
the window's worst hour and gets the note "best time falls in a clear hour".
"Effective cloud" counts thin high cloud at half weight, see
[Weather](Weather).

GO therefore means: the forecast was checked and is clear, calm and dry, and
the target is high. Without a forecast you will never see GO, because
Nachtlotse can't confirm the sky is clear.

The thresholds are starting values, not physics. They live in
`nachtlotse/engine/scoring.py` and can be adjusted there.

## The night verdict

Above the shortlist, one line answers a different question: is the night
worth setting up for at all? It looks at the hourly forecast and finds the
longest unbroken stretch of clear hours inside the dark window. An hour is
clear when the cloud cover is below 40%. An average would hide the shape of
the night, because 40% on average can mean clear until 01:00 and closed
after that.

| Longest clear stretch | Night verdict |
|---|---|
| 3 hours or more | GO |
| 1.5 hours or more | MARGINAL |
| less than 1.5 hours | SKIP |

The line looks like this:

```
Night verdict: GO — clear 21:30–03:10 (5.7 h)
Night verdict: SKIP — longest clear run 1.0 h from 22:00, GO needs 3 h
```

A second line, "Held back by", lists what cost the night time, the
costliest first: cloud cover of 40% or more, wind of 25 km/h or more, a
temperature within 2°C of the dew point, and the Moon when it is at least
50% illuminated and above the horizon. Each comes with the hours it covers.
These only explain the night. The level comes from the clear stretch alone.

Without a forecast the line says "unknown". The same happens when the
forecast covers only part of the dark window and the covered part is too
cloudy to judge the rest, because a short clear stretch there could be
followed by a clear one in the part we can't see.

The night verdict doesn't replace the verdict of each target. Both can
differ: a night can be a GO while a single target is marginal because it
stays low. The thresholds live in `nachtlotse/engine/night.py`.

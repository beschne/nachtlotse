**Deutsch:** [Wie die Rangfolge entsteht](Wie-die-Rangfolge-entsteht)

Nachtlotse ranks targets in three steps: find the best time for each target,
score it, and sort.

## 1. The best time

The dark window of the night (see [Dark Window](Dark-Window)) is sampled at
25 evenly spaced moments. At each moment a target counts as observable when
all of this is true:

- it is at least 20° above the horizon,
- it is above your own horizon line at that direction (see [Configuring Sites](Configuring-Sites)),
- it is at least 30° away from the Moon,
- on an alt-az mount, the frame turns no faster than 1.5° per minute there
  (see [Field Rotation](Field-Rotation)).

The best time is the highest of those moments. A target with no such moment
doesn't appear in the plan at all.

## 2. The score

The score multiplies three numbers between 0 and 1:

score = (altitude ÷ 90°) × fit × reach

Because they are multiplied, a very poor value in any one of them pulls the
score down, however good the other two are.

Fit says how well the target fills your frame. The target's longest
dimension is compared with the short side of your frame. A target exactly
that big gets 1.0. Smaller targets get proportionally less, so a target
filling a quarter of the frame gets 0.25. A target bigger than the frame
loses again as it starts to be cut off. If the size isn't known, fit is 1.0.

Reach says whether the target's light stands out against your sky. Nachtlotse
spreads the target's total brightness over its area, which gives its surface
brightness. It compares that with your site's sky brightness (an SQM value if
you entered one, otherwise an estimate from the Bortle class) plus 3
magnitudes for what stacking gains. A target brighter than that gets 1.0. A
fainter one loses reach over the next 3 magnitudes, down to a minimum of 0.2.
Reach never drops a target completely, because the estimate isn't exact.
Without magnitude, size or sky brightness, reach is 1.0.

## 3. Sorting and the shortlist

All observable targets are sorted by score. The first five form the
shortlist; [favorites](Favorites) that are up get added after them.

## Groups

Targets close enough to share one frame are combined into one entry. Two
targets fit together when their distance is no larger than the short side of
your frame. For a group, fit is calculated from the distance between its
members, and the best time is the best moment when all members are
observable at once.

## The evaluation limit

By default only the 50 brightest catalog objects are checked (`--limit`,
EVALUATE in the app). The catalog is sorted by brightness, so a lower limit
leaves out the faintest objects first. Favorites are always checked. With
`--limit 0` the whole catalog of 236 objects is checked, which takes about
3 seconds.

The verdict (GO, MARGINAL, SKIP) is separate from the score, see [Verdicts](Verdicts).

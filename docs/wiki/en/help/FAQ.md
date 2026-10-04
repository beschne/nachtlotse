# FAQ

**Deutsch:** [Fragen und Antworten](Fragen-und-Antworten)

**Why do I hardly ever see GO?**
GO needs a forecast that is clear, calm and dry and a target above 40°.
Without a forecast, Nachtlotse can't confirm a clear sky and stops at
MARGINAL. See [Verdicts](Verdicts).

**Why does a small object rank low with my wide-field rig?**
Because it would fill only a small part of the frame. That's the "fit" in
the score, see [How Ranking Works](How-Ranking-Works). A longer focal length
would rank it higher.

**My favorite is missing.**
Then it isn't up that night: too low, behind your horizon, too close to the
Moon, or (on alt-az) only near the zenith.

**Does Nachtlotse control my telescope?**
No. It plans. You still point and shoot with your own software.

**Does it work in the southern hemisphere?**
The calculations aren't limited to the north, but they have only been tested
for central Europe so far.

**Can I add objects to the catalog?**
Yes, in `nachtlotse/data/catalog/`. Every value has to come from a real
source (OpenNGC, SIMBAD, NED), see [The Catalog](The-Catalog). For objects
that are just personal favorites, use [Favorites](Favorites) instead.

**Why doesn't Nachtlotse predict comet brightness?**
Because the published formulas didn't match measurements, see
[Data Sources](Data-Sources). Measured values are more honest.

**Where are my settings stored?**
In `nachtlotse/data/*_local.yaml`. Git ignores them, they survive updates
and never get shared.

**Does the AI decide anything?**
No. The optional briefing only rewords what the engine calculated, see
[Nightly Briefing](Nightly-Briefing).

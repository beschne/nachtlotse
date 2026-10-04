# Nachtlotse

**Deutsch:** [Zur deutschen Startseite](Startseite)

Nachtlotse is German for "night pilot". Like a harbor pilot who guides ships
through tricky water, it guides you through the night sky.

It answers one question: what should I shoot tonight? You tell it where you
are and what equipment you use. It checks the sky over your site for that
night and gives you a short list of targets, each with a verdict (GO,
MARGINAL or SKIP) and the reasons for it.

![The Shortlist tab of the Nachtlotse app](https://raw.githubusercontent.com/wiki/beschne/nachtlotse/images/gui-shortlist.png)

## Where to start

- New here: read [Installation](Installation), then [First Run](First-Run).
- Planning a night: [Planning a Night](Planning-a-Night) explains the list and the verdicts.
- Wondering why a target ranks where it does: [How Ranking Works](How-Ranking-Works) and [Verdicts](Verdicts).
- Something looks wrong: [Troubleshooting](Troubleshooting) and the [FAQ](FAQ).

## What it does

Nachtlotse ranks the objects of its built-in catalog (236 deep-sky objects)
for any night you pick. It takes your real horizon and your camera's real
field of view into account. The verdict adds weather, dew risk, moonlight and
how dark the night gets.

It also lists comets, supernovae and novae that are bright enough right now
([Current Events](Current-Events)), shows how a target fits into your camera
frame ([Framing Preview](Framing-Preview)), and tells you which of your sites
has the clearest night ([Best Sky](Best-Sky)).

You can use it from the command line (`lotse`) or as a Mac app (`lotse gui`).
Both use the same engine and give the same answers.

## The rule behind it

All astronomy is calculated, never guessed. Altitudes, times and framing come
from JPL ephemerides through the `skyfield` and `astroplan` libraries, and
tests check them against known values. If something isn't known, for example
the sky darkness of a site or the magnitude of a faint nebula, Nachtlotse
says so instead of making up a number. An AI model is only ever used for the
optional written briefing, and only to phrase numbers the engine already
produced.

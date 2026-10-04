**Deutsch:** [Aktuelle Ereignisse](Aktuelle-Ereignisse)

Besides the fixed catalog, Nachtlotse looks at what is happening in the sky
right now: comets, supernovae and novae. You find them at the end of
`lotse plan`, in their own command, and in the Events tab of the app.

```bash
uv run lotse events                  # everything current, with reasons
uv run lotse plan --no-events        # plan without them (no download)
uv run lotse frame 161P              # frame a comet
uv run lotse frame 2026aaiv          # frame a supernova
```

## What counts

A comet counts if observers reported its brightness in the last 14 days
(source: COBS). Its position is calculated from its orbit, published by the
Minor Planet Center. The brightness is the median of those reports.

A supernova or nova counts if it is on David Bishop's list of active bright
transients ("Latest Supernovae", brighter than 17th magnitude), which gives
its current brightness. Recent novae in our own galaxy come from the IAU
Transient Name Server (TNS). For those, usually only the brightness at
discovery is known, so they're listed with that date but not ranked.

Why not simply take the magnitude from TNS? Because TNS records the
brightness at discovery. SN 2026aaiv in NGC 7331 was found at 17.3 and
reached about 11.5 three weeks later.

## How they are judged

Each event goes through the same checks as a catalog object: it has to rise
high enough, clear your horizon, stay away from the Moon and, on an alt-az
mount, avoid fast [field rotation](Field-Rotation). It also has to be bright
enough for your equipment, see [Brightness Limits](Brightness-Limits). Then
it gets a verdict like everything else.

A comet moves. Nachtlotse uses its position in the middle of the night and
shows how fast it moves, for example "moves 7.3′/h".

Events are only shown for nights within 14 days of today. Brightness
measured now says little about a night two months away.

## The list of the rest

`lotse events` and the lower table in the Events tab show everything that
didn't make it, with the reason: too faint for this rig, not observable
tonight, not yet classified, last brightness report more than a month old,
or no current brightness known.

Where the data comes from and how often it is fetched is described in
[Data Sources](Data-Sources).

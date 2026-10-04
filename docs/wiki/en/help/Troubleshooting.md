**Deutsch:** [Fehlerbehebung](Fehlerbehebung)

## Installation

`uv: command not found`: the installer put uv into `~/.local/bin`, which
isn't on your PATH yet. Open a new terminal, or add
`export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc`.

`Permission denied (publickey)` when cloning: you have no SSH key on GitHub.
Use the HTTPS address instead.

The first run hangs or fails while downloading: that's the 17 MB ephemeris.
It needs internet once, and a company proxy or firewall can block it. Delete
`.cache/skyfield/` and try again on a normal connection.

## Starting

"No sites_local.yaml" or "No rigs_local.yaml": your site or rig file is
missing. The message names the template to copy, see [Configuring Sites](Configuring-Sites).
Nachtlotse never guesses a site or a rig.

`lotse gui` complains about PySide6: run `uv sync --extra gui`. A later plain
`uv sync` removes it again, see [Installation](Installation).

"PNG export needs matplotlib": run `uv sync --extra charts`.

## While planning

"Weather unavailable": Open-Meteo couldn't be reached, for example at a dark
site without reception. The ranking still works, only the weather is
missing. "Beyond forecast range" means the date is more than 16 days ahead.

The header says "nautical only": there is no astronomical darkness that
night, which happens around midsummer. See [Dark Window](Dark-Window).

"No dark window around …": far north in summer the Sun doesn't get 12°
below the horizon. There is nothing to plan.

"Comets unavailable" or "Supernovae unavailable": the source couldn't be
reached and nothing was cached. The plan itself is complete, see
[Offline and Caching](Offline-and-Caching).

A target you expected is missing: check its altitude and your horizon first.
It needs to be at least 20° high, above your horizon line and at least 30°
from the Moon at some moment of the dark window. Also check `--limit`: by
default only the 50 brightest objects are checked.

## Older versions

"Planning failed: interpolating from IERS_Auto using predictive values that
are more than 30.0 days old": fixed in version 3.2.0. Update with `git pull`.

Crashes for dates between late May and mid July: fixed in 3.2.1.

## Something looks astronomically wrong

That's a real bug. Run `uv run pytest` first, then open an issue (or tell
Benno at the club) with your site entry, the rig, the date and what you
expected. The engine is meant to be checkable.

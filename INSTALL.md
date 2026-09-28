# Installing Nachtlotse

A step-by-step setup guide for fellow club members. Written with Claude Code
users in mind: every step is a shell command you can run yourself, or hand to
Claude Code and let it do the typing.

**One thing Claude Code must not do for you:** invent your site coordinates,
your horizon, or your gear specs. Nachtlotse's whole premise is that every
number is real and traceable (see [CLAUDE.md](./CLAUDE.md)). A plausible-looking
guessed latitude produces a plausible-looking wrong plan. Steps 3 and 4 need
*your* numbers.

---

## 0. What you need

| Requirement | Notes |
|---|---|
| **macOS** | The GUI is a native macOS app. The CLI is plain Python and should work on Linux/Windows too, but only macOS is tested. |
| **[`uv`](https://docs.astral.sh/uv/)** | Handles the virtual environment *and* Python itself. |
| **git** | Comes with the Xcode command line tools (`xcode-select --install`). |
| **Python 3.12+** | You do **not** need to install this yourself — `uv` fetches the version pinned in `.python-version`. |

Install `uv` (either line works):

```bash
brew install uv                              # if you use Homebrew
curl -LsSf https://astral.sh/uv/install.sh | sh   # official installer
```

Check it: `uv --version`.

Nothing else is needed. No API key, no account, no cloud service — the
core planner runs fully offline once set up. (Weather is an optional layer
and uses Open-Meteo, which is free and needs no key.)

---

## The short version

If you'd rather let Claude Code drive, `cd` into an empty folder, start
`claude`, and paste this:

> Clone https://github.com/beschne/nachtlotse.git, run `uv sync`, then read
> `INSTALL.md` and walk me through steps 3 and 4 — my observing site and my
> rig. Ask me for the actual numbers, don't guess any of them. When both
> files are in place, run `uv run lotse plan` and show me the result.

The rest of this document is the same thing, done by hand.

---

## 1. Clone the repo

```bash
git clone https://github.com/beschne/nachtlotse.git
cd nachtlotse
```

(SSH instead: `git clone git@github.com:beschne/nachtlotse.git`. If GitHub
says the repository doesn't exist, ask Benno for access rather than assuming
the URL is wrong.)

## 2. Set up the environment

```bash
uv sync
```

This creates `.venv/` and installs `skyfield`, `astroplan`, `astropy`,
`numpy`, `pyyaml`, plus the dev tools. It does **not** install the optional
extras (charts, prose, GUI) — see [step 6](#6-optional-extras).

From here on, prefix commands with `uv run` and you never need to activate
anything: `uv run lotse plan` runs inside the project's own environment.

## 3. Add your observing site(s) — your numbers

```bash
cp nachtlotse/data/sites_local.template.yaml nachtlotse/data/sites_local.yaml
```

Now edit `nachtlotse/data/sites_local.yaml`. The template ships with two
real Taunus sites (Volkssternwarte Hochtaunus, Großer Feldberg) as working
examples — keep them, replace them, or add your own below them. **The first
entry in the file is the default site** for `lotse plan` when you don't pass
`--site`, so put your home site on top.

Per site:

| Field | Required | Where to get it |
|---|---|---|
| `name` | yes | whatever you call the place |
| `lat_deg`, `lon_deg` | yes | decimal degrees, N/E positive. Right-click in Apple Maps / Google Maps, or read it off your mount's GPS. Four decimals (~10 m) is plenty. |
| `elevation_m` | yes | a topographic map, or your phone's altimeter |
| `tz` | no | IANA zone, defaults to `Europe/Berlin` |
| `region`, `address`, `aliases` | no | display only — `aliases` lets you type `--site Feldberg` |
| `bortle` | no | free text like `"5 (urban fringe)"`; also parsed into a number (`"3-4"` → 3.5) and used for the surface-brightness ranking. Leave it out if you genuinely don't know — don't guess. |
| `zenith_sky_brightness_mag_arcsec2` | no | only if you own an SQM meter and actually measured it near new moon. Overrides the Bortle estimate. |
| `horizon_points` / `sector` | no | your local skyline |

**About the horizon.** This is the field that makes the verdicts honest, and
it's worth the effort for your home site:

- `horizon_points: [[az_deg, alt_deg], ...]` — measured minimum altitude per
  azimuth (0° = North, clockwise), linearly interpolated, wrapping at 360°.
  Twenty-ish points around the horizon is a good survey. A phone clinometer
  app plus a compass gets you there in half an hour.
- `sector: [start_deg, end_deg]` or `[start_deg, end_deg, min_alt_deg]` —
  shorthand for "only this clockwise arc is open sky", everything outside
  becomes a wall. Perfect for a balcony.
- Omit both for an unobstructed 360° view.

Skip it and Nachtlotse will happily recommend a target your neighbour's roof
is sitting in front of.

## 4. Add your rig(s) — your gear

```bash
cp nachtlotse/data/rigs_local.template.yaml nachtlotse/data/rigs_local.yaml
```

Edit `nachtlotse/data/rigs_local.yaml`. As with sites, **the first entry is
the default rig**. The template already contains ready-made entries for a
Seestar S30 Pro (native and on an EQ wedge), a Seestar S50 Pro, a RedCat 51
with an ASI2600MC Duo, and a TEC 160 FL — if you own one of those, you're
done; delete the rest.

Otherwise, per rig:

- `optics.focal_length_mm`, `optics.aperture_mm` — from the scope's spec sheet.
  Use the *effective* focal length if you shoot with a reducer or Barlow.
- `sensor.width_px`, `sensor.height_px`, `sensor.pixel_um` — from the camera's
  spec sheet. Together with focal length these give field of view and pixel
  scale, which is how framing gets scored.
- `mount.kind` — `"altaz"` or `"eq"`. This matters: alt-az rigs get penalized
  for field rotation near the zenith, EQ rigs don't. It's a *setup* choice,
  not fixed hardware — a Seestar on a polar-aligned wedge is `"eq"`. List the
  same hardware twice under different `aliases` if you use it both ways.
- `name`, `aliases`, and the `.name` labels are free text; `aliases` is what
  makes `--rig S30P` work.

## 5. First run

```bash
uv run lotse sites     # your sites, as parsed — check them here first
uv run lotse rigs      # your rigs, with computed FoV and pixel scale
uv run lotse plan      # tonight's shortlist for site #1 + rig #1
```

On the very first run, `skyfield` downloads the JPL ephemeris `de421.bsp`
(~17 MB) once into `.cache/skyfield/`. That needs network. Everything after
that is offline except the optional weather layer.

Sanity-check the install while you're at it:

```bash
uv run pytest
```

The test suite checks the engine against known astronomical values and never
touches your local site/rig files, so it passes either way.

A few flags worth knowing on day one (full list in [README.md](./README.md)):

```bash
uv run lotse plan --site "Großer Feldberg" --rig S30P
uv run lotse plan --date 2026-11-14     # plan a future night
uv run lotse plan --limit 0             # evaluate the whole catalog, not just the 50 brightest
uv run lotse plan --type galaxy         # one object type only (repeatable)
uv run lotse best-sky --radius-km 50    # which of your sites has the clearest sky tonight
```

## 6. Optional extras

Each front-end extra is its own dependency group. **Install all the ones you
want in a single command** — a later bare `uv sync` syncs the environment back
to exactly what's declared and removes extras you didn't ask for:

```bash
uv sync --all-extras          # charts + prose + GUI
uv sync --extra gui           # or just the ones you want
```

| Extra | Gives you | Cost |
|---|---|---|
| `charts` | `lotse plan --chart` — the shortlist as an alt/az polar PNG (matplotlib) | free |
| `gui` | `lotse gui` — the native macOS app (PySide6) | free |
| `prose` | `lotse plan --prose` — an LLM-written nightly briefing | needs an Anthropic API key, billed per call |

### The GUI

```bash
uv sync --extra gui
uv run lotse gui
```

Six tabs over the same engine as the CLI, against your own
`sites_local.yaml` / `rigs_local.yaml`. No demo data anywhere — if a tab is
empty, it's because nothing's up.

### The nightly briefing (`--prose`)

Opt-in, and only ever used for *phrasing* — every altitude, window, and
verdict still comes from the engine. Nothing is sent to Anthropic unless you
pass `--prose` (or click Generate in the GUI).

```bash
uv sync --extra prose
export ANTHROPIC_API_KEY=sk-ant-...
uv run lotse plan --prose
```

Or keep the key in a gitignored file instead of your shell profile:

```bash
cp nachtlotse/data/prose_local.template.yaml nachtlotse/data/prose_local.yaml
# then edit it: api_key, and optionally which model
```

That file holds a real secret in plain text — treat it like any other
credentials file. Missing key or missing extra fails loudly, never silently.

### Favorites (optional)

Objects you always want in the shortlist regardless of ranking — a recurrent
nova like T CrB sitting at 10th magnitude between eruptions, say:

```bash
cp nachtlotse/data/favorites_local.template.yaml nachtlotse/data/favorites_local.yaml
```

List them by `catalog_id` exactly as written in
`nachtlotse/data/catalog/*.yaml`. They're marked `★` everywhere and are
always evaluated, even past `--limit`.

## 7. A Dock icon (optional)

There's no code-signed installer — the repo ships the CLI and `lotse gui`.
If you want Nachtlotse in the Dock, a three-file `.app` wrapper does the job.
It bakes in absolute paths to *your* checkout and *your* `uv`, so it's
machine-specific and deliberately gitignored — build your own rather than
copying someone else's:

```bash
APP="$HOME/Applications/Nachtlotse.app"
REPO="$(pwd)"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp nachtlotse/gui/assets/app_icon.icns "$APP/Contents/Resources/"

cat > "$APP/Contents/MacOS/Nachtlotse" <<EOF
#!/bin/bash
cd "$REPO" || exit 1
exec "$(command -v uv)" run lotse gui
EOF
chmod +x "$APP/Contents/MacOS/Nachtlotse"

cat > "$APP/Contents/Info.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>Nachtlotse</string>
    <key>CFBundleDisplayName</key><string>Nachtlotse</string>
    <key>CFBundleIdentifier</key><string>local.nachtlotse</string>
    <key>CFBundleVersion</key><string>1.0</string>
    <key>CFBundleShortVersionString</key><string>1.0</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleExecutable</key><string>Nachtlotse</string>
    <key>CFBundleIconFile</key><string>app_icon.icns</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>LSMinimumSystemVersion</key><string>12.0</string>
</dict>
</plist>
EOF
```

Run it from `~/Applications`, then drag it to the Dock. Needs the `gui` extra
installed. If the icon doesn't refresh, `touch "$APP"`.

## 8. Staying up to date

```bash
git pull
uv sync          # add --all-extras if you use them
```

Your `*_local.yaml` files are gitignored, so sites, rigs, favorites, and API
key all survive a `git pull` untouched. Nothing you configure locally ever
gets committed or shared.

---

## Troubleshooting

**`uv: command not found`** — the installer put it in `~/.local/bin`, which
isn't on your `PATH` yet. Open a new terminal, or add
`export PATH="$HOME/.local/bin:$PATH"` to `~/.zshrc`.

**`Permission denied (publickey)` on clone** — you have no SSH key on GitHub.
Use the HTTPS URL in step 1 instead.

**"No sites_local.yaml" / "No rigs_local.yaml"** — step 3 or 4 is missing.
The message names the exact template to copy. Expected behaviour, not a bug:
the engine never guesses a site or a rig.

**`lotse gui` complains about PySide6** — `uv sync --extra gui`. Also check a
bare `uv sync` didn't remove it again (see step 6).

**First run hangs or fails while downloading** — that's the 17 MB JPL
ephemeris. Needs network once; a corporate proxy or firewall will block it.
Delete `.cache/skyfield/` and retry on a normal connection.

**"Weather unavailable"** — Open-Meteo wasn't reachable (offline at a dark
site, for instance). The sky-geometry ranking and verdicts still work; only
the weather factor drops out. "Beyond forecast range" is different: the date
you asked for is past Open-Meteo's 16-day horizon.

**`lotse plan` feels slow** — it evaluates the 50 brightest catalog objects by
default. `--limit 0` for everything, a lower `--limit` for speed; the catalog
is loaded brightest-first, so a low limit gives up the faintest objects
first, never something bright.

**Something looks astronomically wrong** — that's a real bug and worth
reporting, not working around. `uv run pytest` first, then open an issue (or
tell Benno at the club) with your site entry, the rig, the date, and what you
expected. The engine is meant to be checkable.

---

## Where to read next

- [README.md](./README.md) — what it does, all CLI flags, GUI tour
- [CLAUDE.md](./CLAUDE.md) — architecture and the guiding principle
- [ROADMAP.md](./ROADMAP.md) — what's planned, what's deliberately out of scope
- [STATUS.md](./STATUS.md) — module-by-module state

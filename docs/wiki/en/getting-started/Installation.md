# Installation

**Deutsch:** [Installieren](Installieren)

Every step below is a shell command. You can type them yourself or let
Claude Code do it.

One thing Claude Code must not do for you: invent your site coordinates,
your horizon or your equipment data. A guessed latitude gives you a plan
that looks fine and is wrong. The pages [Configuring Sites](Configuring-Sites)
and [Configuring Rigs](Configuring-Rigs) need your own numbers.

## What you need

| Requirement | Notes |
|---|---|
| macOS | The app is a native Mac app. The command line is plain Python and should run on Linux and Windows, but only macOS is tested. |
| [uv](https://docs.astral.sh/uv/) | Manages the Python environment and Python itself. |
| git | Comes with the Xcode command line tools (`xcode-select --install`). |
| Python 3.12 or newer | No need to install it yourself, uv fetches the right version. |

Install uv with one of these, then check it with `uv --version`:

```bash
brew install uv                                   # with Homebrew
curl -LsSf https://astral.sh/uv/install.sh | sh   # official installer
```

You don't need an API key, an account or a cloud service. Once set up, the
planner works offline. Weather and current events are optional extras that
use free sources.

## With Claude Code

Open an empty folder, start `claude` and paste this:

> Clone https://github.com/beschne/nachtlotse.git, run `uv sync`, then read
> the Nachtlotse wiki pages "Configuring Sites" and "Configuring Rigs" and
> walk me through my observing site and my rig. Ask me for the actual
> numbers, don't guess any of them. When both files are in place, run
> `uv run lotse plan` and show me the result.

## 1. Get the code

```bash
git clone https://github.com/beschne/nachtlotse.git
cd nachtlotse
```

With SSH: `git clone git@github.com:beschne/nachtlotse.git`.

## 2. Set up the environment

```bash
uv sync
```

This creates `.venv/` and installs everything the planner needs. From now on
put `uv run` in front of every command, for example `uv run lotse plan`.
There's nothing to activate.

## 3. Your sites and your equipment

Copy the two templates and fill in your own data. How to do that is
explained in [Configuring Sites](Configuring-Sites) and [Configuring Rigs](Configuring-Rigs).

```bash
cp nachtlotse/data/sites_local.template.yaml nachtlotse/data/sites_local.yaml
cp nachtlotse/data/rigs_local.template.yaml nachtlotse/data/rigs_local.yaml
```

Git ignores both copies, so your data never ends up in the repository.

## 4. Optional extras

Some features need extra packages. Install all the ones you want in one
command. A later plain `uv sync` removes extras you didn't list again.

```bash
uv sync --all-extras          # everything
uv sync --extra gui           # or only what you need
```

| Extra | What it adds | Cost |
|---|---|---|
| `charts` | PNG files: `lotse plan --chart` and `lotse frame` | free |
| `gui` | the Mac app, `lotse gui` | free |
| `prose` | a written nightly briefing, `lotse plan --prose` | needs an Anthropic API key, paid per request |

Continue with [First Run](First-Run).

## A Dock icon

There is no signed installer. If you want Nachtlotse in the Dock, build a
small `.app` wrapper. It contains the paths of your own checkout and your own
uv, so build it yourself rather than copying someone else's. Run this inside
the repository folder:

```bash
APP="$HOME/Applications/Nachtlotse.app"
REPO="$(pwd)"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp nachtlotse/gui/assets/app_icon.icns "$APP/Contents/Resources/"

cat > "$APP/Contents/MacOS/Nachtlotse" <<EOS
#!/bin/bash
cd "$REPO" || exit 1
exec "$(command -v uv)" run lotse gui
EOS
chmod +x "$APP/Contents/MacOS/Nachtlotse"

cat > "$APP/Contents/Info.plist" <<'EOS'
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
EOS
```

Start it once from `~/Applications`, then drag it to the Dock. It needs the
`gui` extra. If the icon doesn't show up, run `touch "$APP"`.

## Updating

```bash
git pull
uv sync          # plus --all-extras or your --extra flags
```

Your own files (`*_local.yaml`) are ignored by git and stay as they are.

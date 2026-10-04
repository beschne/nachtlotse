**English:** [Installation](Installation)

Jeder Schritt unten ist ein Befehl im Terminal. Du kannst ihn selbst
eintippen oder Claude Code machen lassen.

Eines darf Claude Code dabei nicht: deine Standortkoordinaten, deinen
Horizont oder die Daten deiner Ausrüstung erfinden. Ein geschätzter
Breitengrad ergibt einen Plan, der gut aussieht und falsch ist. Für
[Standorte einrichten](Standorte-einrichten) und
[Teleskope und Kameras](Teleskope-und-Kameras) brauchst du deine eigenen
Zahlen.

## Was du brauchst

| Voraussetzung | Hinweis |
|---|---|
| macOS | Die App ist eine native Mac-App. Die Kommandozeile ist reines Python und sollte auch unter Linux und Windows laufen, getestet ist aber nur macOS. |
| [uv](https://docs.astral.sh/uv/) | Verwaltet die Python-Umgebung und Python selbst. |
| git | Kommt mit den Xcode-Kommandozeilenwerkzeugen (`xcode-select --install`). |
| Python 3.12 oder neuer | Musst du nicht selbst installieren, das erledigt uv. |

uv installierst du mit einer dieser Zeilen, danach prüfst du es mit
`uv --version`:

```bash
brew install uv                                   # mit Homebrew
curl -LsSf https://astral.sh/uv/install.sh | sh   # offizieller Installer
```

Du brauchst keinen API-Schlüssel, kein Konto und keinen Cloud-Dienst. Nach
der Einrichtung läuft der Planer offline. Wetter und aktuelle Ereignisse
sind Zusätze, die kostenlose Quellen nutzen.

## Mit Claude Code

Öffne einen leeren Ordner, starte `claude` und füge das hier ein:

> Klone https://github.com/beschne/nachtlotse.git, führe `uv sync` aus, lies
> dann die Wiki-Seiten „Standorte einrichten“ und „Teleskope und Kameras“ und
> geh mit mir meinen Standort und meine Ausrüstung durch. Frag mich nach den
> echten Zahlen und rate keine davon. Wenn beide Dateien da sind, führe
> `uv run lotse plan` aus und zeig mir das Ergebnis.

## 1. Code holen

```bash
git clone https://github.com/beschne/nachtlotse.git
cd nachtlotse
```

Mit SSH: `git clone git@github.com:beschne/nachtlotse.git`.

## 2. Umgebung einrichten

```bash
uv sync
```

Das legt `.venv/` an und installiert alles, was der Planer braucht. Ab jetzt
setzt du `uv run` vor jeden Befehl, zum Beispiel `uv run lotse plan`. Zu
aktivieren gibt es nichts.

## 3. Deine Standorte und deine Ausrüstung

Kopiere die beiden Vorlagen und trage deine eigenen Daten ein. Wie das geht,
steht in [Standorte einrichten](Standorte-einrichten) und
[Teleskope und Kameras](Teleskope-und-Kameras).

```bash
cp nachtlotse/data/sites_local.template.yaml nachtlotse/data/sites_local.yaml
cp nachtlotse/data/rigs_local.template.yaml nachtlotse/data/rigs_local.yaml
```

Git ignoriert beide Kopien, deine Daten landen also nie im Repository.

## 4. Zusätze

Manche Funktionen brauchen zusätzliche Pakete. Installiere alle, die du
willst, in einem Befehl. Ein späteres einfaches `uv sync` entfernt Zusätze,
die du dort nicht aufführst, wieder.

```bash
uv sync --all-extras          # alles
uv sync --extra gui           # oder nur das, was du brauchst
```

| Zusatz | Was er bringt | Kosten |
|---|---|---|
| `charts` | PNG-Dateien: `lotse plan --chart` und `lotse frame` | keine |
| `gui` | die Mac-App, `lotse gui` | keine |
| `prose` | ein geschriebenes Nachtbriefing, `lotse plan --prose` | braucht einen Anthropic-API-Schlüssel, kostet pro Anfrage |

Weiter geht es mit [Erster Start](Erster-Start).

## Ein Dock-Symbol

Einen signierten Installer gibt es nicht. Wenn du Nachtlotse im Dock haben
willst, baust du dir eine kleine `.app`-Hülle. Sie enthält die Pfade deines
eigenen Checkouts und deines eigenen uv, also bau sie selbst und kopiere
nicht die von jemand anderem. Führe das im Ordner des Repositorys aus:

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

Starte sie einmal aus `~/Applications` und zieh sie dann ins Dock. Sie
braucht den Zusatz `gui`. Wenn das Symbol nicht erscheint, hilft
`touch "$APP"`.

## Aktualisieren

```bash
git pull
uv sync          # plus --all-extras oder deine --extra-Angaben
```

Deine eigenen Dateien (`*_local.yaml`) ignoriert git, sie bleiben, wie sie
sind.

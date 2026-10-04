# Nachtbriefing

**English:** [Nightly Briefing](Nightly-Briefing)

Das Briefing ist eine kurze geschriebene Zusammenfassung der Nacht, so wie
sie dir ein erfahrener Beobachter geben würde. Es ist freiwillig und die
einzige Stelle, an der ein KI-Modell (Claude von Anthropic) beteiligt ist.

```bash
uv sync --extra prose
export ANTHROPIC_API_KEY=sk-ant-...
uv run lotse plan --prose
```

In der App öffnest du den Reiter Briefing und drückst Generate.

## Was das Modell darf und was nicht

Das Modell bekommt nur die Fakten, die Nachtlotse schon berechnet hat:
Dunkelphase, Mond, Wetter und die Shortlist mit Höhen, Zeiten und
Bewertungen. Es darf keine Zahl, Uhrzeit oder Bewertung nennen, die nicht in
diesen Fakten steht. Es formuliert um, es entscheidet nichts. Ohne Briefing
ist der Plan genau derselbe.

An Anthropic geht nichts, solange du nicht `--prose` angibst oder Generate
drückst. Fehlen Schlüssel oder Zusatz, bekommst du eine klare Fehlermeldung.

## Den Schlüssel in einer Datei ablegen

Statt der Umgebungsvariable kannst du den Schlüssel in eine Datei schreiben,
die git ignoriert:

```bash
cp nachtlotse/data/prose_local.template.yaml nachtlotse/data/prose_local.yaml
```

In der Datei kannst du auch das Modell festlegen. Sie enthält ein echtes
Geheimnis im Klartext, behandle sie also wie eine Passwortdatei.

Jede Anfrage kostet einen kleinen Betrag auf deinem Anthropic-Konto.

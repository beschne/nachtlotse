**Deutsch:** [Nachtbriefing](Nachtbriefing)

The briefing is a short written summary of the night, as you might hear it
from an experienced observer. It's optional and the only place where an AI
model (Claude, by Anthropic) is involved.

```bash
uv sync --extra prose
export ANTHROPIC_API_KEY=sk-ant-...
uv run lotse plan --prose
```

In the app, open the Briefing tab and press Generate.

## What the model may and may not do

The model only gets the facts Nachtlotse has already calculated: dark
window, Moon, weather, the shortlist with altitudes, times and verdicts. It
is told not to state any number, time or verdict that isn't in those facts.
It rewords, it doesn't decide. Without the briefing, the plan is exactly the
same.

Nothing is sent to Anthropic unless you pass `--prose` or press Generate.
If the key or the extra is missing, you get a clear error message.

## Keeping the key in a file

Instead of the environment variable, you can put the key into a file that
git ignores:

```bash
cp nachtlotse/data/prose_local.template.yaml nachtlotse/data/prose_local.yaml
```

The file can also name the model to use. It holds a real secret in plain
text, so treat it like any password file.

Each request costs a small amount on your Anthropic account.

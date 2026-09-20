"""Nightly briefing — the LLM prose layer, and the only place in this
project allowed to call the Claude API.

Per CLAUDE.md's Guiding principle ("The engine decides. An LLM formulates
at most the prose — never the astronomy."): this module never computes
anything. It hands the model a plain-text statement of facts already
decided by `planning.py` (`build_briefing_facts`) and asks it to phrase
those facts as readable prose, nothing else — strip this module out
entirely and the plan's own numbers/verdicts are unchanged.

Unlike `weather/open_meteo.py` (always attempted by `plan_night`, silently
degrading if unreachable), this module is never called unless the CLI's
`--prose` flag is passed — an LLM call is not something `lotse plan` does
by default. Once requested, a failure (package not installed, no API key,
request error) is not swallowed either: `ProseUnavailable` propagates so
the caller can fail loudly, the same contract `chart_export.py` uses for
a missing `charts` extra.

The API key and model both resolve through `prose_local.yaml` first
(`data/store.load_prose_config()`, entirely optional — see
`prose_local.template.yaml`), falling back to the `ANTHROPIC_API_KEY`
environment variable and `DEFAULT_MODEL` respectively when that file
doesn't set them.
"""

from __future__ import annotations

import os
from zoneinfo import ZoneInfo

from nachtlotse.data import store
from nachtlotse.engine.models import Target, WeatherSummary
from nachtlotse.planning import (
    NightPlan,
    NightPlanForBestRig,
    RankedGroup,
    RankedTargetForBestRig,
)

# Matches CLAUDE.md's own "Anthropic LLM recommendation" for this exact
# use case: phrasing, not computing, so the workhorse default suffices.
DEFAULT_MODEL = "claude-sonnet-5"

# A nightly briefing is a paragraph or two, not an essay, but 500 turned
# out too tight for a full 5-entry shortlist (SHORTLIST_SIZE) with even
# one sentence each plus an intro/outro — real output was getting cut
# off mid-sentence. 1024 leaves real headroom; the length instruction in
# SYSTEM_PROMPT keeps the model from just filling that budget with prose.
DEFAULT_MAX_TOKENS = 1024

SYSTEM_PROMPT = (
    "You are writing a short, friendly nightly astrophotography briefing "
    "for an amateur about to head out to their telescope. Every fact "
    "below — altitudes, azimuths, times, verdicts, weather figures — was "
    "already computed by a deterministic planning engine; you are not "
    "an astronomer here, only a writer. Phrase these facts as readable "
    "prose. Do not invent, adjust, round differently, or infer any "
    "number, time, altitude, or verdict beyond what is given. Do not "
    "recommend any target that isn't already in the shortlist below. If "
    "you are unsure how to phrase something, omit it rather than guess. "
    "Output plain text only, for display in a terminal — no Markdown at "
    "all: no **bold**, no # headings, no -/* bullet or numbered lists. "
    "Use each target's exact label and separator (e.g. \"A + B\") as "
    "given, not your own variant. Keep it tight: one short paragraph for "
    "the overall picture (dark window, Moon, weather), then at most one "
    "or two sentences per shortlisted target — never a full paragraph "
    "each. Finish every sentence you start rather than running out of "
    "room partway through the shortlist."
)


class ProseUnavailable(Exception):
    """The `prose` extra isn't installed, no API key is configured, or
    the Anthropic API request itself failed.

    Callers must treat this as a hard failure, not a fallback — unlike
    weather, prose is only ever attempted because the user explicitly
    asked for it (`--prose`), so silently omitting it would hide that
    they didn't get what they asked for.
    """


def _target_label(target: Target) -> str:
    return f"{target.catalog_id} {target.name}".strip()


def _entry_targets(ranked: object) -> tuple[Target, ...]:
    if isinstance(ranked, RankedGroup):
        return ranked.targets
    return (ranked.target,)  # type: ignore[attr-defined]


def _entry_label(ranked: object) -> str:
    return " + ".join(_target_label(target) for target in _entry_targets(ranked))


def _weather_line(weather: WeatherSummary | None) -> str:
    if weather is None:
        return "Weather: unavailable (no forecast could be fetched)."
    return (
        f"Weather: clouds up to {weather.max_cloud_cover_pct:.0f}% "
        f"(avg {weather.avg_cloud_cover_pct:.0f}%), wind up to "
        f"{weather.max_wind_kmh:.0f} km/h, dew margin "
        f"{weather.min_dew_point_spread_c:.1f}°C."
    )


def build_briefing_facts(plan: NightPlan | NightPlanForBestRig) -> str:
    """A compact, plain-text statement of every fact `plan` already
    carries — the only input `generate_nightly_briefing` gives the model.

    Built straight from `plan`'s own fields rather than reusing `cli.py`'s
    print formatting, so the model's ground truth stays stable even if
    display formatting changes later. Covers the shortlist only, not the
    full ranked table — the shortlist is already the actionable summary
    (see `planning.SHORTLIST_SIZE`).

    Works for both `NightPlan` (one rig for the whole plan) and
    `NightPlanForBestRig` (a rig chosen per entry, via `--best-rig`) —
    the latter names each entry's own winning rig instead of one rig for
    the whole briefing.
    """
    local_tz = ZoneInfo(plan.site.tz)
    plan_rig_name = plan.rig.name if isinstance(plan, NightPlan) else None

    lines = [f"Site: {plan.site.name}"]
    if plan_rig_name is not None:
        lines.append(f"Rig: {plan_rig_name}")
    lines.append(
        f"Dark window: {plan.evening_start.astimezone(local_tz):%Y-%m-%d %H:%M} "
        f"to {plan.morning_end.astimezone(local_tz):%H:%M %Z}."
    )
    lines.append(f"Moon illumination: {plan.moon_illumination_pct:.0f}%.")
    lines.append(_weather_line(plan.weather))
    lines.append("")
    lines.append("Shortlist (already ranked, most promising first):")

    if not plan.shortlist:
        lines.append("(none — nothing clears tonight's constraints)")

    for rank, entry in enumerate(plan.shortlist, start=1):
        ranked = entry.ranked
        local_time = ranked.best_time.astimezone(local_tz)
        detail_bits = [
            f"verdict {entry.verdict.level}",
            f"altitude {ranked.pos.alt_deg:.0f}°",
            f"azimuth {ranked.pos.az_deg:.0f}°",
            f"best time {local_time:%Y-%m-%d %H:%M %Z}",
        ]
        if isinstance(ranked, RankedTargetForBestRig):
            detail_bits.append(f"rig {ranked.rig.name}")
        lines.append(f"{rank}. {_entry_label(ranked)} — " + "; ".join(detail_bits) + ".")
        for reason in entry.verdict.reasons:
            lines.append(f"   reason: {reason}")

    return "\n".join(lines)


def _import_anthropic():
    """The lazy-import seam, factored out so tests can force the `prose`
    extra's "not installed" path without needing to actually uninstall
    it — same pattern as `chart_export._import_matplotlib`."""
    import anthropic

    return anthropic


def _resolve_api_key() -> str | None:
    """`prose_local.yaml`'s `api_key`, if set there, else the
    `ANTHROPIC_API_KEY` environment variable, else None."""
    config = store.load_prose_config()
    if config is not None and config.api_key:
        return config.api_key
    return os.environ.get("ANTHROPIC_API_KEY")


def resolve_model(explicit_model: str | None = None) -> str:
    """`explicit_model` if given, else `prose_local.yaml`'s `model`, else
    `DEFAULT_MODEL` — the same precedence `_resolve_api_key` uses for the
    key. Public so `cli.py` can show which model actually ran."""
    if explicit_model is not None:
        return explicit_model
    config = store.load_prose_config()
    if config is not None and config.model:
        return config.model
    return DEFAULT_MODEL


def _request_briefing_text(facts: str, *, model: str, max_tokens: int) -> str:
    """The actual Anthropic API call, factored out from
    `generate_nightly_briefing` so tests can monkeypatch this one seam
    instead of mocking the `anthropic` package itself.

    Raises `ProseUnavailable` for every failure mode: the extra isn't
    installed, no API key is configured, or the request itself failed
    (network, auth, rate limit, ...) — deliberately not narrowed to a
    specific `anthropic` exception type, since any of them means the
    same thing to a caller here: no briefing this time.
    """
    try:
        anthropic = _import_anthropic()
    except ImportError as exc:
        raise ProseUnavailable(
            "Nightly briefing needs the `anthropic` package, which isn't "
            "installed — run `uv sync --extra prose` and try again."
        ) from exc

    api_key = _resolve_api_key()
    if not api_key:
        raise ProseUnavailable(
            "Nightly briefing needs an Anthropic API key — set api_key in "
            "nachtlotse/data/prose_local.yaml (copy "
            "prose_local.template.yaml to create it) or the "
            "ANTHROPIC_API_KEY environment variable, and try again."
        )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": facts}],
        )
    except Exception as exc:
        raise ProseUnavailable(f"Nightly briefing request failed: {exc}") from exc

    return "".join(
        block.text for block in response.content if block.type == "text"
    ).strip()


def generate_nightly_briefing(
    plan: NightPlan | NightPlanForBestRig,
    *,
    model: str | None = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """A short prose briefing phrasing `plan`'s already-decided facts —
    `lotse plan --prose`'s own entry point.

    `model`, left as None, resolves via `resolve_model` (
    `prose_local.yaml`'s own `model` field, else `DEFAULT_MODEL`); pass
    it explicitly to override both.

    Raises `ProseUnavailable` on any failure; see `_request_briefing_text`.
    Never called unless explicitly requested (see the module docstring).
    """
    facts = build_briefing_facts(plan)
    return _request_briefing_text(
        facts, model=resolve_model(model), max_tokens=max_tokens
    )

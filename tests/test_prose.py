"""Nightly briefing tests (nachtlotse/prose.py).

`anthropic` is an optional extra (`uv sync --extra prose`) — every path
here is exercised via `prose._import_anthropic`'s seam (real or faked),
so the suite never needs the real package installed or a real API call.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from nachtlotse import planning, prose
from nachtlotse.data import store
from nachtlotse.engine import ephemeris
from nachtlotse.engine.models import (
    HorizonProfile,
    Mount,
    Optics,
    Rig,
    Sensor,
    Site,
    Target,
    Verdict,
    WeatherSummary,
)


@pytest.fixture(autouse=True)
def _no_local_prose_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts from "no prose_local.yaml" — decouples the
    suite from whatever a developer's own gitignored file (if any)
    happens to contain, the same reasoning `template_sites`/
    `template_rigs` decouple tests from real site/rig lists. Tests that
    care about config-based resolution override this explicitly."""
    monkeypatch.setattr(store, "load_prose_config", lambda: None)

SITE = Site(
    name="Test Site",
    lat_deg=50.0,
    lon_deg=8.0,
    elevation_m=200.0,
    tz="Europe/Berlin",
    horizon=HorizonProfile(points=[]),
)

RIG = Rig(
    name="Test Rig",
    optics=Optics(name="Test Optics", focal_length_mm=250.0, aperture_mm=50.0),
    sensor=Sensor(name="Test Sensor", width_px=4000, height_px=3000, pixel_um=3.0),
    mount=Mount(name="EQ Test Mount", kind="eq"),
)

OTHER_RIG = Rig(
    name="Other Test Rig",
    optics=Optics(name="Other Optics", focal_length_mm=500.0, aperture_mm=80.0),
    sensor=Sensor(name="Test Sensor", width_px=4000, height_px=3000, pixel_um=3.0),
    mount=Mount(name="EQ Test Mount", kind="eq"),
)

_WHEN = datetime(2026, 9, 20, 22, 0, tzinfo=UTC)

_TARGET_A = Target(name="target a", catalog_id="TA1", ra_deg=10.0, dec_deg=20.0)
_TARGET_B = Target(name="target b", catalog_id="TB2", ra_deg=11.0, dec_deg=20.0)

_WEATHER = WeatherSummary(
    max_cloud_cover_pct=15.0,
    avg_cloud_cover_pct=8.0,
    max_wind_kmh=12.0,
    min_dew_point_spread_c=3.5,
)


def _pos(alt_deg: float, az_deg: float) -> ephemeris.AltAz:
    return ephemeris.AltAz(alt_deg=alt_deg, az_deg=az_deg, distance_au=1.0)


def _night_plan(shortlist_ranked, ranked=None) -> planning.NightPlan:
    shortlist = [
        planning.ShortlistEntry(
            row, Verdict(level="GO", reasons=["clear sky forecast and good conditions"])
        )
        for row in shortlist_ranked
    ]
    return planning.NightPlan(
        site=SITE,
        rig=RIG,
        evening_start=_WHEN,
        morning_end=_WHEN,
        moon_illumination_pct=42.0,
        moonrise=None,
        moonset=None,
        weather=_WEATHER,
        ranked=ranked if ranked is not None else list(shortlist_ranked),
        shortlist=shortlist,
    )


def test_build_briefing_facts_includes_site_rig_moon_weather_and_target() -> None:
    ranked = planning.RankedTarget(
        target=_TARGET_A, best_time=_WHEN, pos=_pos(55.0, 180.0), fit=0.9, reach=1.0
    )
    facts = prose.build_briefing_facts(_night_plan([ranked]))

    assert "Site: Test Site" in facts
    assert "Rig: Test Rig" in facts
    assert "Moon illumination: 42%" in facts
    assert "clouds up to 15%" in facts
    assert "TA1 target a" in facts
    assert "verdict GO" in facts
    assert "altitude 55°" in facts
    assert "azimuth 180°" in facts
    assert "reason: clear sky forecast and good conditions" in facts


def test_build_briefing_facts_joins_a_ranked_groups_member_names() -> None:
    group = planning.RankedGroup(
        targets=(_TARGET_A, _TARGET_B),
        best_time=_WHEN,
        pos=_pos(60.0, 90.0),
        fit=0.8,
        reach=1.0,
    )
    facts = prose.build_briefing_facts(_night_plan([group]))

    assert "TA1 target a + TB2 target b" in facts


def test_build_briefing_facts_notes_an_empty_shortlist() -> None:
    facts = prose.build_briefing_facts(_night_plan([]))

    assert "none — nothing clears tonight's constraints" in facts


def test_build_briefing_facts_for_best_rig_plan_names_each_entrys_own_rig() -> None:
    row = planning.RankedTargetForBestRig(
        target=_TARGET_A,
        rig=OTHER_RIG,
        best_time=_WHEN,
        pos=_pos(70.0, 200.0),
        fit=1.0,
        reach=1.0,
    )
    plan = planning.NightPlanForBestRig(
        site=SITE,
        evening_start=_WHEN,
        morning_end=_WHEN,
        moon_illumination_pct=10.0,
        moonrise=None,
        moonset=None,
        weather=None,
        ranked=[row],
        shortlist=[
            planning.BestRigShortlistEntry(row, Verdict(level="MARGINAL", reasons=["x"]))
        ],
    )
    facts = prose.build_briefing_facts(plan)

    # No single whole-plan "Rig:" line — each entry names its own winner.
    assert not any(line.startswith("Rig: ") for line in facts.splitlines())
    assert "rig Other Test Rig" in facts
    assert "Weather: unavailable" in facts


def test_generate_nightly_briefing_raises_when_anthropic_is_not_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom():
        raise ImportError("simulated: anthropic not installed")

    monkeypatch.setattr(prose, "_import_anthropic", _boom)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    ranked = planning.RankedTarget(
        target=_TARGET_A, best_time=_WHEN, pos=_pos(55.0, 180.0), fit=0.9, reach=1.0
    )
    with pytest.raises(prose.ProseUnavailable, match="extra"):
        prose.generate_nightly_briefing(_night_plan([ranked]))


def test_generate_nightly_briefing_raises_when_no_api_key_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prose, "_import_anthropic", lambda: object())
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    ranked = planning.RankedTarget(
        target=_TARGET_A, best_time=_WHEN, pos=_pos(55.0, 180.0), fit=0.9, reach=1.0
    )
    with pytest.raises(prose.ProseUnavailable, match="ANTHROPIC_API_KEY"):
        prose.generate_nightly_briefing(_night_plan([ranked]))


def test_resolve_api_key_prefers_prose_local_yaml_over_the_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    monkeypatch.setattr(
        store, "load_prose_config", lambda: store.ProseConfig(api_key="config-key")
    )

    assert prose._resolve_api_key() == "config-key"


def test_resolve_api_key_falls_back_to_the_env_var_when_config_has_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    monkeypatch.setattr(store, "load_prose_config", lambda: store.ProseConfig())

    assert prose._resolve_api_key() == "env-key"


def test_resolve_model_prefers_an_explicit_argument_over_everything() -> None:
    assert prose.resolve_model("explicit-model") == "explicit-model"


def test_resolve_model_prefers_prose_local_yaml_over_the_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        store, "load_prose_config", lambda: store.ProseConfig(model="configured-model")
    )

    assert prose.resolve_model() == "configured-model"


def test_resolve_model_falls_back_to_the_default_when_nothing_is_configured() -> None:
    assert prose.resolve_model() == prose.DEFAULT_MODEL


class _FakeTextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.content = [_FakeTextBlock(text)]


class _FakeMessages:
    def __init__(self, captured: dict, response_text: str, error: Exception | None) -> None:
        self._captured = captured
        self._response_text = response_text
        self._error = error

    def create(self, **kwargs):
        self._captured.update(kwargs)
        if self._error is not None:
            raise self._error
        return _FakeResponse(self._response_text)


class _FakeClient:
    def __init__(self, captured: dict, response_text: str, error: Exception | None) -> None:
        self.messages = _FakeMessages(captured, response_text, error)


class _FakeAnthropicModule:
    def __init__(self, captured: dict, response_text: str = "", error: Exception | None = None) -> None:
        self._captured = captured
        self._response_text = response_text
        self._error = error

    def Anthropic(self, **kwargs):
        self._captured["client_kwargs"] = kwargs
        return _FakeClient(self._captured, self._response_text, self._error)


def test_generate_nightly_briefing_returns_the_models_text_and_sends_the_facts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}
    monkeypatch.setattr(
        prose, "_import_anthropic", lambda: _FakeAnthropicModule(captured, "Clear skies ahead.")
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    ranked = planning.RankedTarget(
        target=_TARGET_A, best_time=_WHEN, pos=_pos(55.0, 180.0), fit=0.9, reach=1.0
    )
    plan = _night_plan([ranked])

    briefing = prose.generate_nightly_briefing(plan)

    assert briefing == "Clear skies ahead."
    assert captured["model"] == prose.DEFAULT_MODEL
    assert captured["system"] == prose.SYSTEM_PROMPT
    assert "TA1 target a" in captured["messages"][0]["content"]
    assert captured["client_kwargs"]["api_key"] == "test-key"


def test_generate_nightly_briefing_uses_prose_local_yamls_key_and_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}
    monkeypatch.setattr(
        prose, "_import_anthropic", lambda: _FakeAnthropicModule(captured, "Configured briefing.")
    )
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        store,
        "load_prose_config",
        lambda: store.ProseConfig(api_key="configured-key", model="configured-model"),
    )

    ranked = planning.RankedTarget(
        target=_TARGET_A, best_time=_WHEN, pos=_pos(55.0, 180.0), fit=0.9, reach=1.0
    )
    briefing = prose.generate_nightly_briefing(_night_plan([ranked]))

    assert briefing == "Configured briefing."
    assert captured["model"] == "configured-model"
    assert captured["client_kwargs"]["api_key"] == "configured-key"


def test_generate_nightly_briefing_wraps_a_request_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        prose,
        "_import_anthropic",
        lambda: _FakeAnthropicModule({}, error=RuntimeError("network down")),
    )
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    ranked = planning.RankedTarget(
        target=_TARGET_A, best_time=_WHEN, pos=_pos(55.0, 180.0), fit=0.9, reach=1.0
    )
    with pytest.raises(prose.ProseUnavailable, match="network down"):
        prose.generate_nightly_briefing(_night_plan([ranked]))

"""Nachtlotse — Streamlit MVP (M5).

`uv sync --extra ui` once, then `uv run streamlit run nachtlotse/ui/app.py`.

Same rule as `cli.py`: this file is the UI boundary. It calls
`nachtlotse.planning.plan_night()` for every number on the page and adds
no astronomy of its own — verdict light, hero target, backups, and the
altitude curve all come straight from the engine's own output.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from nachtlotse import planning
from nachtlotse.data import store
from nachtlotse.engine import ephemeris

_VERDICT_BOX = {
    "GO": st.success,
    "MARGINAL": st.warning,
    "SKIP": st.error,
}

_MIN_USEFUL_ALTITUDE_DEG = 20.0  # engine.constraints._DEFAULT_MIN_ALT_DEG
_ALTITUDE_CURVE_SAMPLES = 97
_BACKUP_COUNT = 8


def _format_arcmin(size_arcmin: float) -> str:
    """0 decimals reads fine for nebulae/galaxies (tens of arcmin), but
    rounds small planetary nebulae (often well under 1 arcmin) to "0'".
    """
    return f"{size_arcmin:.0f}" if size_arcmin >= 1.0 else f"{size_arcmin:.2f}"


def _require_configuration() -> None:
    try:
        store.require_sites()
        store.require_rigs()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()


@st.cache_data(ttl=300, show_spinner="Planning tonight's sky…")
def _cached_plan(site_name: str, rig_name: str, date_key: str) -> planning.NightPlan:
    site_record = store.get_site_record(site_name)
    rig_record = store.get_rig_record(rig_name)
    local_tz = ZoneInfo(site_record.site.tz)
    target_date = date.fromisoformat(date_key)
    # Noon local time: unambiguously daytime, so dark_window picks the
    # night starting that evening (same trick as cli.py's --date).
    when = datetime(
        target_date.year, target_date.month, target_date.day, 12, 0, tzinfo=local_tz
    )
    return planning.plan_night(site_record.site, rig_record.rig, when)


def _altitude_curve_frame(plan: planning.NightPlan, local_tz: ZoneInfo) -> pd.DataFrame:
    hero = plan.ranked[0]
    series = ephemeris.altitude_series(
        plan.site,
        hero.target,
        plan.evening_start,
        plan.morning_end,
        num_samples=_ALTITUDE_CURVE_SAMPLES,
    )
    return pd.DataFrame(
        {
            f"{hero.target.name} altitude": [pos.alt_deg for _when, pos in series],
            "Min useful altitude": _MIN_USEFUL_ALTITUDE_DEG,
        },
        index=pd.DatetimeIndex(
            [when.astimezone(local_tz) for when, _pos in series], name="Local time"
        ),
    )


def _backups_frame(plan: planning.NightPlan, local_tz: ZoneInfo) -> pd.DataFrame:
    rows = plan.ranked[1 : 1 + _BACKUP_COUNT]
    return pd.DataFrame(
        {
            "Target": [f"{row.target.catalog_id} {row.target.name}" for row in rows],
            "Max Alt (°)": [round(row.pos.alt_deg, 1) for row in rows],
            "Az (°)": [round(row.pos.az_deg, 1) for row in rows],
            "Fit": [round(row.fit, 2) for row in rows],
            "Best time": [
                row.best_time.astimezone(local_tz).strftime("%Y-%m-%d %H:%M %Z")
                for row in rows
            ],
        }
    )


def main() -> None:
    st.set_page_config(page_title="Nachtlotse", page_icon="🔭", layout="centered")
    st.title("🔭 Nachtlotse")
    st.caption("What should I shoot tonight?")

    _require_configuration()

    with st.sidebar:
        st.header("Session")
        site_name = st.selectbox("Site", store.list_site_names())
        rig_name = st.selectbox("Rig", store.list_rig_names())
        planned_date = st.date_input("Night of", value=datetime.now(UTC).date())

    plan = _cached_plan(site_name, rig_name, planned_date.isoformat())
    local_tz = ZoneInfo(plan.site.tz)

    st.subheader(f"{plan.site.name} — {plan.rig.name}")
    st.write(
        f"Dark window: **{plan.evening_start.astimezone(local_tz):%Y-%m-%d %H:%M}** – "
        f"**{plan.morning_end.astimezone(local_tz):%H:%M %Z}**"
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Moon illumination", f"{plan.moon_illumination_pct:.0f}%")
    if plan.weather is not None:
        metric_cols[1].metric(
            "Cloud cover (max)", f"{plan.weather.max_cloud_cover_pct:.0f}%"
        )
        metric_cols[2].metric("Wind (max)", f"{plan.weather.max_wind_kmh:.0f} km/h")
        metric_cols[3].metric(
            "Dew margin (min)", f"{plan.weather.min_dew_point_spread_c:.1f}°C"
        )
    else:
        metric_cols[1].metric(
            "Weather", "N/A", help="Unavailable (offline or Open-Meteo unreachable)"
        )

    if not plan.ranked:
        st.error(
            "No catalog target clears altitude/moon/night/horizon/rotation "
            "constraints tonight."
        )
        return

    hero = plan.ranked[0]
    verdict = plan.verdict
    assert verdict is not None  # a ranked hero always yields a verdict

    box = _VERDICT_BOX[verdict.level]
    box(f"**{verdict.level}** — hero target: **{hero.target.name}**")
    for reason in verdict.reasons:
        st.markdown(f"- {reason}")

    st.markdown("### Hero target")
    hero_cols = st.columns(4)
    hero_cols[0].metric("Max altitude", f"{hero.pos.alt_deg:.0f}°")
    hero_cols[1].metric("Azimuth", f"{hero.pos.az_deg:.0f}°")
    hero_cols[2].metric("Framing fit", f"{hero.fit:.2f}")
    hero_cols[3].metric(
        "Best time", hero.best_time.astimezone(local_tz).strftime("%H:%M")
    )
    width_arcmin, height_arcmin = hero.target.size_arcmin
    st.caption(
        f"{hero.target.catalog_id} · magnitude {hero.target.magnitude:.1f} · "
        f"size {_format_arcmin(width_arcmin)}′ × {_format_arcmin(height_arcmin)}′"
    )

    st.markdown("### Altitude tonight")
    st.line_chart(_altitude_curve_frame(plan, local_tz))

    if len(plan.ranked) > 1:
        st.markdown("### Backups")
        st.dataframe(_backups_frame(plan, local_tz), hide_index=True, width="stretch")


if __name__ == "__main__":
    main()

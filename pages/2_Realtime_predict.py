from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from factory_toto.brand import ICON_PATH, write_brand_assets
from factory_toto.config import COLUMN_LABELS, DEFAULT_MODEL_DIR
from factory_toto.data import prepare_plant_frame
from factory_toto.engine import TotoEngine, evaluate_alerts
from factory_toto.realtime import (
    append_tick,
    count_past_predictions,
    count_rows,
    read_history,
    read_prediction_history,
    reset_db,
    save_forecast,
    seed_history,
)
from factory_toto.ui import THEME, page_banner

st.set_page_config(
    page_title="Real-time prediction",
    page_icon="🌽",
    layout="wide",
    initial_sidebar_state="expanded",
)
if not ICON_PATH.exists():
    write_brand_assets()

st.markdown(THEME, unsafe_allow_html=True)
st.markdown(
    page_banner(
        "Real-time corn prediction",
        "Live fermenter data is written to a local database. The top chart is live vs Toto; the bottom chart is the delta (live minus prediction).",
        kicker="Live line · F-1 fermenter",
    ),
    unsafe_allow_html=True,
)

CHART_CHOICES = [
    "brix_pct",
    "sweetness_index",
    "fructose_pct",
    "fermenter_temp_c",
    "ph",
    "residual_starch_pct",
    "enzyme_activity_u",
]


def label_of(col: str) -> str:
    return COLUMN_LABELS.get(col, col.replace("_", " "))


@st.cache_resource(show_spinner=False)
def get_engine() -> TotoEngine:
    return TotoEngine(DEFAULT_MODEL_DIR)


def kpi_card(title: str, value: str, hint: str) -> None:
    st.markdown(
        f'<div class="kpi"><div class="label">{title}</div>'
        f'<div class="value">{value}</div><div class="hint">{hint}</div></div>',
        unsafe_allow_html=True,
    )


def prediction_delta(hist: pd.DataFrame, pred_hist: pd.DataFrame | None, col: str) -> pd.DataFrame:
    if pred_hist is None or pred_hist.empty or col not in hist.columns:
        return pd.DataFrame()
    left = hist[["timestamp", col]].copy()
    left["timestamp"] = pd.to_datetime(left["timestamp"]).dt.floor("s")
    right = pred_hist[["timestamp", "median", "p10", "p90"]].copy()
    right["timestamp"] = pd.to_datetime(right["timestamp"]).dt.floor("s")
    out = left.merge(right, on="timestamp", how="inner")
    if out.empty:
        return out
    out["delta"] = out[col] - out["median"]
    return out.sort_values("timestamp").reset_index(drop=True)


def draw_live_chart(
    hist: pd.DataFrame,
    forecast,
    col: str,
    pred_hist: pd.DataFrame | None = None,
) -> go.Figure:
    compared = prediction_delta(hist, pred_hist, col)
    step_ms = 5 * 60 * 1000
    if len(hist) >= 2:
        step = pd.Series(hist["timestamp"]).diff().dt.total_seconds().median()
        if pd.notna(step) and step > 0:
            step_ms = float(step) * 1000

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.62, 0.38],
        subplot_titles=(
            f"{label_of(col)} · live vs Toto",
            "Delta · live − prediction",
        ),
    )

    fig.add_trace(
        go.Scatter(
            x=hist["timestamp"],
            y=hist[col],
            name="Live (database)",
            line=dict(color="#134e4a", width=2.8),
            mode="lines",
        ),
        row=1,
        col=1,
    )
    if not compared.empty:
        fig.add_trace(
            go.Scatter(
                x=compared["timestamp"],
                y=compared["median"],
                name="Toto history",
                line=dict(color="#0d9488", width=2.2, dash="dot"),
                mode="lines",
            ),
            row=1,
            col=1,
        )
    if forecast is not None and col in forecast.columns:
        i = forecast.columns.index(col)
        fig.add_trace(
            go.Scatter(
                x=list(forecast.future_index) + list(forecast.future_index[::-1]),
                y=list(forecast.p90[i]) + list(forecast.p10[i][::-1]),
                fill="toself",
                fillcolor="rgba(249, 115, 22, 0.18)",
                line=dict(color="rgba(0,0,0,0)"),
                name="Next P10-P90",
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=forecast.future_index,
                y=forecast.median[i],
                name="Next prediction",
                line=dict(color="#ea580c", width=3, dash="dash"),
            ),
            row=1,
            col=1,
        )

    if not compared.empty:
        colors = ["#ea580c" if val < 0 else "#0d9488" for val in compared["delta"]]
        fig.add_trace(
            go.Bar(
                x=compared["timestamp"],
                y=compared["delta"],
                name="Delta",
                marker=dict(color=colors, line=dict(width=0)),
                width=step_ms * 0.78,
                hovertemplate="Delta %{y:+.3f}<extra>live − Toto</extra>",
            ),
            row=2,
            col=1,
        )
        fig.add_hline(y=0, line_dash="solid", line_color="#94a3b8", line_width=1.2, row=2, col=1)

    if not hist.empty:
        now_ts = hist["timestamp"].iloc[-1]
        for row in (1, 2):
            fig.add_vline(
                x=now_ts,
                line_dash="dot",
                line_color="#fb923c",
                line_width=1.3,
                row=row,
                col=1,
                annotation_text="now" if row == 1 else None,
                annotation_font_color="#c2410c",
            )

    fig.update_layout(
        template="plotly_white",
        height=640,
        margin=dict(l=52, r=20, t=56, b=36),
        legend=dict(orientation="h", y=1.12),
        plot_bgcolor="#f8fffd",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#134e4a"),
        bargap=0.12,
        hovermode="x unified",
    )
    fig.update_yaxes(title_text=label_of(col), gridcolor="#d1f0ea", row=1, col=1)
    fig.update_yaxes(title_text="Delta", gridcolor="#d1f0ea", zeroline=True, row=2, col=1)
    fig.update_xaxes(gridcolor="#d1f0ea", row=1, col=1)
    fig.update_xaxes(gridcolor="#d1f0ea", row=2, col=1)
    return fig


with st.sidebar:
    if ICON_PATH.exists():
        st.image(str(ICON_PATH), width=84)
    st.markdown("### Live corn line")
    live = st.toggle("Live auto-update", value=True, key="rt_live")
    refresh_s = st.selectbox(
        "Refresh time",
        [5, 10, 15, 30, 60],
        index=1,
        format_func=lambda s: f"{s} seconds",
        key="rt_refresh",
    )
    step_min = st.selectbox("Plant step per refresh", [5, 10, 15], index=0, format_func=lambda m: f"{m} min of batch")
    st.caption("Each refresh writes one new fermenter sample into SQLite, then redraws from the database.")
    chart_col = st.selectbox("Chart signal", CHART_CHOICES, format_func=label_of)
    horizon = st.select_slider("Predict ahead (steps)", options=[12, 24, 48, 96], value=24)
    context_n = st.select_slider("History for model", options=[128, 256, 384], value=256)
    c1, c2 = st.columns(2)
    with c1:
        seed_now = st.button("Seed line")
    with c2:
        wipe = st.button("Clear DB")

if wipe:
    reset_db()
    st.session_state["rt_need_seed"] = True
    st.session_state["rt_backfilled_cols"] = []
if seed_now or count_rows() == 0 or st.session_state.get("rt_need_seed"):
    seed_history(step_minutes=int(step_min))
    st.session_state["rt_need_seed"] = False
    st.session_state["rt_backfilled_cols"] = []
    st.caption("Seeded local database with corn fermenter history.")


@st.fragment(run_every=int(refresh_s) if live else None)
def live_panel() -> None:
    try:
        hist = append_tick(step_minutes=int(step_min)) if st.session_state.get("rt_live", True) else read_history()
    except Exception as exc:
        st.error(f"Live sample failed: {exc}")
        hist = read_history()
    if hist.empty:
        st.warning("Database is empty. Press Seed line.")
        return

    last = hist.iloc[-1]
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi_card("Sweet degree", f"{last['brix_pct']:.1f}", "Brix % · live")
    with k2:
        kpi_card("Sweetness", f"{last['sweetness_index']:.1f}", "index · live")
    with k3:
        kpi_card("Fermenter", f"{last['fermenter_temp_c']:.1f} C", f"stage {last['stage']}")
    with k4:
        kpi_card("pH", f"{last['ph']:.2f}", f"batch {last['batch_id']}")

    status = "LIVE" if st.session_state.get("rt_live", True) else "PAUSED"
    cls = "ok" if st.session_state.get("rt_live", True) else "warn"
    st.markdown(
        f'<span class="badge {cls}">{status}</span> &nbsp; '
        f"Last sample {pd.Timestamp(last['timestamp']).strftime('%H:%M:%S')} &nbsp; "
        f"Wall clock {datetime.now().strftime('%H:%M:%S')} &nbsp; "
        f"Refresh {refresh_s}s &nbsp; "
        f"Rows in DB {count_rows():,}",
        unsafe_allow_html=True,
    )

    forecast = None
    pred_hist = pd.DataFrame()
    try:
        frame = prepare_plant_frame(hist)
        use_cols = [c for c in [chart_col, "brix_pct", "sweetness_index"] if c in frame.columns]
        use_cols = list(dict.fromkeys(use_cols))
        last_ts = hist["timestamp"].iloc[-1]
        if use_cols and len(frame) >= 64:
            engine = get_engine()
            holdout = min(int(horizon), max(0, len(frame) - 64))
            done_cols = list(st.session_state.get("rt_backfilled_cols", []))
            need_backfill = chart_col not in done_cols or (
                count_past_predictions(chart_col, until=last_ts) < 8
            )
            if need_backfill and holdout >= 8:
                with st.spinner("Building prediction history…"):
                    origin = frame.iloc[:-holdout]
                    backfill = engine.forecast(
                        origin,
                        horizon=holdout,
                        context_length=min(int(context_n), len(origin)),
                        columns=use_cols,
                    )
                    save_forecast(
                        "F-1",
                        backfill.columns,
                        frame.index[-holdout:],
                        backfill.median,
                        backfill.p10,
                        backfill.p90,
                        issued_at=origin.index[-1],
                    )
                st.session_state["rt_backfilled_cols"] = list(dict.fromkeys(done_cols + use_cols))
            with st.spinner("Updating Toto forecast…"):
                forecast = engine.forecast(
                    frame,
                    horizon=int(horizon),
                    context_length=min(int(context_n), len(frame)),
                    columns=use_cols,
                )
                save_forecast(
                    "F-1",
                    forecast.columns,
                    forecast.future_index,
                    forecast.median,
                    forecast.p10,
                    forecast.p90,
                    issued_at=last_ts,
                )
        pred_hist = read_prediction_history(chart_col, until=last_ts, limit=240)
        if not pred_hist.empty:
            window_start = hist.tail(240)["timestamp"].min()
            pred_hist = pred_hist[pred_hist["timestamp"] >= window_start]
    except Exception as exc:
        st.error(f"Prediction skipped: {exc}")

    chart_hist = hist.tail(240)
    compared = prediction_delta(chart_hist, pred_hist, chart_col)
    st.plotly_chart(draw_live_chart(chart_hist, forecast, chart_col, pred_hist), width="stretch")

    if not compared.empty:
        last_cmp = compared.iloc[-1]
        mae = float(compared["delta"].abs().mean())
        st.caption(
            f"Last delta: {last_cmp['delta']:+.2f} (live {last_cmp[chart_col]:.2f} − Toto {last_cmp['median']:.2f})"
            f" · MAE {mae:.2f} · teal = Toto low, orange = Toto high"
        )

    if forecast is not None:
        alerts = evaluate_alerts(forecast)
        if not alerts:
            st.markdown('<span class="badge ok">NEXT STEPS LOOK STABLE</span>', unsafe_allow_html=True)
        else:
            for alert in alerts[:4]:
                when = pd.Timestamp(alert["when"]).strftime("%H:%M")
                st.write(
                    f"**{label_of(alert['column'])}** {alert['level']} · about {alert['value']:.1f} near {when}"
                )

    live_col, pred_col = st.columns(2)
    with live_col:
        st.caption("Live samples")
        tail = hist.tail(12)[
            ["timestamp", "stage", "brix_pct", "sweetness_index", "fructose_pct", "fermenter_temp_c", "ph"]
        ]
        st.dataframe(tail, width="stretch", hide_index=True)
    with pred_col:
        st.caption("Delta history")
        if compared.empty:
            st.info("Delta appears after the first Toto forecast.")
        else:
            show = compared.tail(12).rename(
                columns={
                    chart_col: "live",
                    "median": "predicted",
                    "delta": "delta",
                }
            )
            st.dataframe(
                show[["timestamp", "live", "predicted", "delta", "p10", "p90"]],
                width="stretch",
                hide_index=True,
            )


live_panel()

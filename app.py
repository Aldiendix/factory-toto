from __future__ import annotations

import warnings
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from factory_toto.brand import HERO_PATH, ICON_PATH, TITLE, write_brand_assets
from factory_toto.config import (
    COLUMN_LABELS,
    DEFAULT_CONTEXT,
    DEFAULT_HORIZON,
    DEFAULT_MODEL_DIR,
    DEFAULT_THRESHOLDS,
    SAMPLE_CSV,
    SWEET_CSV,
)
from factory_toto.data import load_table, prepare_plant_frame
from factory_toto.engine import TotoEngine, evaluate_alerts, latest_kpis, result_to_frame
from factory_toto.sample import write_sample_csv
from factory_toto.sweet_corn import write_sweet_csv
from factory_toto.ui import THEME, page_banner

warnings.filterwarnings(
    "ignore",
    message="Using `json`-module for json-handling",
    category=UserWarning,
)

if not HERO_PATH.exists() or not ICON_PATH.exists():
    write_brand_assets()

st.set_page_config(
    page_title=TITLE,
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(THEME, unsafe_allow_html=True)


@st.cache_resource(show_spinner=False)
def get_engine() -> TotoEngine:
    return TotoEngine(DEFAULT_MODEL_DIR)


def label_of(col: str) -> str:
    return COLUMN_LABELS.get(col, col.replace("_", " "))


def kpi_card(title: str, value: str, hint: str) -> None:
    st.markdown(
        f'<div class="kpi"><div class="label">{title}</div>'
        f'<div class="value">{value}</div><div class="hint">{hint}</div></div>',
        unsafe_allow_html=True,
    )


def plot_series(result, col: str) -> go.Figure:
    i = result.columns.index(col)
    ctx_x = result.context_index
    fut_x = result.future_index
    ctx_y = result.context[i]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(fut_x) + list(fut_x[::-1]),
            y=list(result.p90[i]) + list(result.p10[i][::-1]),
            fill="toself",
            fillcolor="rgba(249, 115, 22, 0.18)",
            line=dict(color="rgba(0,0,0,0)"),
            name="P10-P90",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ctx_x,
            y=ctx_y,
            name="History",
            line=dict(color="#334155", width=2.4),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=fut_x,
            y=result.median[i],
            name="Forecast (P50)",
            line=dict(color="#0d9488", width=3),
        )
    )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="#f8fffd",
        margin=dict(l=48, r=24, t=48, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        title=dict(text=label_of(col), font=dict(color="#134e4a", size=18)),
        yaxis_title=label_of(col),
        xaxis_title="",
        height=380,
        font=dict(color="#134e4a"),
    )
    fig.update_xaxes(gridcolor="#d1f0ea", zeroline=False)
    fig.update_yaxes(gridcolor="#d1f0ea", zeroline=False)
    return fig


def load_raw_table(source: str, uploaded) -> pd.DataFrame:
    if source == "Upload file":
        if uploaded is None:
            return pd.DataFrame()
        return load_table(uploaded.getvalue(), uploaded.name)
    if source == "Corn sweet fermentation":
        if not SWEET_CSV.exists():
            write_sweet_csv(SWEET_CSV)
        return load_table(SWEET_CSV)
    if not SAMPLE_CSV.exists():
        write_sample_csv(SAMPLE_CSV)
    return load_table(SAMPLE_CSV)


st.markdown(
    page_banner(
        TITLE,
        "See the next shift for sweet degree, fermentation, temperature, power, and other plant sensors — on this computer.",
    ),
    unsafe_allow_html=True,
)
if HERO_PATH.exists():
    st.markdown('<div class="hero-wrap">', unsafe_allow_html=True)
    st.image(str(HERO_PATH), width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

with st.sidebar:
    if ICON_PATH.exists():
        st.image(str(ICON_PATH), width=84)
    st.markdown(f"### {TITLE}")
    st.caption("Local Toto 2.0 forecast. Use Build datasets to make a corn-sweet file.")
    st.markdown("### Data")
    source = st.radio(
        "Plant line",
        ["Corn sweet fermentation", "Extrusion sample", "Upload file"],
        key="plant_source",
    )
    if st.session_state.get("_last_plant_source") not in (None, source):
        st.session_state.forecast = None
        st.session_state.pop("forecast_signals", None)
    st.session_state._last_plant_source = source
    uploaded = None
    if source == "Upload file":
        uploaded = st.file_uploader("CSV or Excel", type=["csv", "xlsx", "xls"])
        st.caption("Need a timestamp column plus numeric sensors.")
    elif source == "Corn sweet fermentation":
        st.caption("Corn → mash → fermenter. Predict Brix, sweetness, fructose, pH, temperature.")
    else:
        st.caption("Sample extrusion line at 15-minute intervals.")

    st.markdown("### Forecast")
    context_length = st.select_slider("Context length", options=[256, 384, 512, 768, 1024], value=DEFAULT_CONTEXT)
    horizon = st.select_slider("Horizon (steps)", options=[24, 48, 96, 192, 288], value=DEFAULT_HORIZON)
    st.caption("Sample step = 15 min, so 96 steps is about 24 hours.")

    st.markdown("### Model")
    st.code(str(Path(DEFAULT_MODEL_DIR)), language="text")
    if DEFAULT_MODEL_DIR.exists():
        st.markdown('<span class="badge ok">LOCAL WEIGHTS READY</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge crit">RUN download_model.py</span>', unsafe_allow_html=True)

try:
    raw = load_raw_table(source, uploaded)
except Exception as exc:
    st.error(str(exc))
    st.stop()

if raw.empty:
    st.info("Upload a plant CSV or pick a sample line in the sidebar. You can also open Build datasets.")
    st.stop()

tank_id = None
if "tank_id" in raw.columns:
    tanks = sorted(raw["tank_id"].astype(str).unique())
    tank_id = st.selectbox("Fermenter", tanks)

try:
    frame = prepare_plant_frame(raw, tank_id=tank_id)
except Exception as exc:
    st.error(str(exc))
    st.stop()

if frame.empty:
    st.info("No numeric sensors found in this file.")
    st.stop()

available = list(frame.columns)
sweet_pref = [
    "brix_pct",
    "sweetness_index",
    "fructose_pct",
    "fermenter_temp_c",
    "ph",
    "residual_starch_pct",
]
default_cols = [c for c in sweet_pref if c in available]
if not default_cols:
    default_cols = [c for c in DEFAULT_THRESHOLDS if c in available] or available[:4]
if "forecast_signals" not in st.session_state:
    st.session_state.forecast_signals = default_cols
else:
    kept = [c for c in st.session_state.forecast_signals if c in available]
    st.session_state.forecast_signals = kept or default_cols
selected = st.multiselect("Signals to forecast", available, key="forecast_signals")
if not selected:
    st.warning("Select at least one signal.")
    st.stop()

kpis = latest_kpis(frame[selected])
cols = st.columns(min(4, len(selected)))
for i, col in enumerate(selected[:4]):
    with cols[i]:
        val = kpis.get(col)
        kpi_card(label_of(col), f"{val:,.2f}" if val is not None else "-", "latest observation")

run = st.button("Run local Toto forecast", type="primary")

if "forecast" not in st.session_state:
    st.session_state.forecast = None

if run:
    engine = get_engine()
    with st.spinner("Forecasting on this machine..."):
        st.session_state.forecast = engine.forecast(
            frame,
            horizon=horizon,
            context_length=context_length,
            columns=selected,
        )

result = st.session_state.forecast
if result is not None and any(col not in frame.columns for col in result.columns):
    st.session_state.forecast = None
    result = None
if result is None:
    st.caption("Set context / horizon, then run the forecast. First load may take a minute on CPU.")
    preview, meta = st.tabs(["History preview", "Data quality"])
    with preview:
        st.line_chart(frame[selected].tail(context_length))
    with meta:
        st.write(
            {
                "rows": int(len(frame)),
                "signals": selected,
                "start": str(frame.index.min()),
                "end": str(frame.index.max()),
                "missing_values": int(frame[selected].isna().sum().sum()),
            }
        )
    st.stop()

alerts = evaluate_alerts(result)
left, right = st.columns([2, 1])
with left:
    st.subheader("Shift outlook")
    st.caption(
        f"Device: {result.device}  |  context {len(result.context_index)} steps  |  "
        f"horizon {len(result.future_index)} steps  |  local weights"
    )
with right:
    if not alerts:
        st.markdown('<span class="badge ok">NO LIMIT BREACH IN FORECAST</span>', unsafe_allow_html=True)
    elif any(a["level"] == "critical" for a in alerts):
        st.markdown('<span class="badge crit">CRITICAL RISK IN HORIZON</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge warn">WARNING IN HORIZON</span>', unsafe_allow_html=True)

if alerts:
    st.markdown("#### Limit watch")
    for alert in alerts:
        when = pd.Timestamp(alert["when"]).strftime("%Y-%m-%d %H:%M")
        verb = "high" if alert["mode"] == "high" else "low"
        st.write(
            f"**{label_of(alert['column'])}** | {alert['level'].upper()} | "
            f"{verb} side may reach **{alert['value']:.2f}** around {when} "
            f"(warn {alert['warn']}, crit {alert['crit']})"
        )

chart_col = st.selectbox("Chart signal", result.columns, format_func=label_of)
st.plotly_chart(plot_series(result, chart_col), width="stretch")

table = result_to_frame(result)
st.markdown("#### Forecast table")
st.dataframe(table, width="stretch", hide_index=True)

csv_buf = BytesIO()
table.to_csv(csv_buf, index=False)
st.download_button(
    "Download forecast CSV",
    data=csv_buf.getvalue(),
    file_name="plant_forecast.csv",
    mime="text/csv",
)

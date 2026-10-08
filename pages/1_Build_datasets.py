from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from factory_toto.brand import ICON_PATH, write_brand_assets
from factory_toto.config import COLUMN_LABELS, DATA_DIR
from factory_toto.sweet_corn import (
    DEFAULT_SWEET_COLUMNS,
    VARIABLE_GROUPS,
    generate_sweet_corn,
)
from factory_toto.ui import THEME, page_banner

st.set_page_config(
    page_title="Build datasets",
    page_icon="🌽",
    layout="wide",
    initial_sidebar_state="expanded",
)
if not ICON_PATH.exists():
    write_brand_assets()

st.markdown(THEME, unsafe_allow_html=True)
st.markdown(
    page_banner(
        "Build plant datasets",
        "Make a corn-to-sweet fermentation file, pick many factory variants, then download or save it for Predict.",
        kicker="Dataset workshop · corn sweet line",
    ),
    unsafe_allow_html=True,
)

st.markdown(
    """
Corn is steeped, liquefied, saccharified, then converted in the fermenter.
**Sweet degree (Brix)** and **sweetness index** rise as glucose turns toward fructose.
Use this page to build a CSV. Open **Predict factaroy variable** to forecast it.
"""
)

with st.sidebar:
    if ICON_PATH.exists():
        st.image(str(ICON_PATH), width=84)
    st.markdown("### Line")
    st.write("Corn sweet fermentation")
    days = st.slider("Days of history", 7, 45, 21)
    step = st.selectbox("Sample every", [5, 10, 15, 30], index=2, format_func=lambda m: f"{m} min")
    tanks = st.slider("Fermenters", 1, 4, 1)
    seed = st.number_input("Random seed", min_value=1, max_value=9999, value=11)
    missing = st.slider("Missing telemetry %", 0.0, 5.0, 1.2, 0.1)
    st.caption("More fermenters = long file with tank_id. Predict one tank at a time.")

picked: list[str] = []
st.subheader("Factory variants")
st.caption("Tick every sensor you want in the dataset. Sweet degree is selected by default.")
cols = st.columns(2)
groups = list(VARIABLE_GROUPS.items())
for i, (group, items) in enumerate(groups):
    with cols[i % 2]:
        st.markdown(f"**{group}**")
        for key, label in items:
            default_on = key in DEFAULT_SWEET_COLUMNS
            if st.checkbox(label, value=default_on, key=f"var_{key}"):
                picked.append(key)

st.markdown("#### Extra custom sensor")
c1, c2, c3 = st.columns(3)
with c1:
    extra_name = st.text_input("Column name", placeholder="e.g. foam_level_pct")
with c2:
    extra_base = st.number_input("Base value", value=10.0)
with c3:
    extra_noise = st.number_input("Noise", value=0.5, min_value=0.0)

build = st.button("Build dataset", type="primary")

if "dataset" not in st.session_state:
    st.session_state.dataset = None

if build:
    if not picked:
        st.warning("Select at least one variant.")
    else:
        df = generate_sweet_corn(
            days=int(days),
            step_minutes=int(step),
            tanks=int(tanks),
            seed=int(seed),
            columns=picked,
            missing_pct=float(missing),
        )
        name = extra_name.strip().replace(" ", "_")
        if name:
            safe = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in name)
            rng = pd.Series(
                extra_base + extra_noise * (2 * (pd.RangeIndex(len(df)) % 17) / 17 - 1),
                index=df.index,
            )
            df[safe] = rng.round(3)
        st.session_state.dataset = df

df = st.session_state.dataset
if df is None:
    st.info("Choose variants, then press Build dataset.")
    st.stop()

label_of = lambda c: COLUMN_LABELS.get(c, c.replace("_", " "))
numeric = df.select_dtypes("number")
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f'<div class="kpi"><div class="label">Rows</div><div class="value">{len(df):,}</div><div class="hint">including all tanks</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="kpi"><div class="label">Sensors</div><div class="value">{numeric.shape[1]}</div><div class="hint">numeric variants</div></div>', unsafe_allow_html=True)
with k3:
    tanks_n = df["tank_id"].nunique() if "tank_id" in df.columns else 1
    st.markdown(f'<div class="kpi"><div class="label">Tanks</div><div class="value">{tanks_n}</div><div class="hint">fermenters</div></div>', unsafe_allow_html=True)
with k4:
    if "brix_pct" in df.columns:
        st.markdown(f'<div class="kpi"><div class="label">Last Brix</div><div class="value">{df["brix_pct"].dropna().iloc[-1]:.1f}</div><div class="hint">sweet degree</div></div>', unsafe_allow_html=True)
    elif "sweetness_index" in df.columns:
        st.markdown(f'<div class="kpi"><div class="label">Last sweetness</div><div class="value">{df["sweetness_index"].dropna().iloc[-1]:.1f}</div><div class="hint">index</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="kpi"><div class="label">From</div><div class="value">{df["timestamp"].min().strftime("%m-%d")}</div><div class="hint">start date</div></div>', unsafe_allow_html=True)

chart_cols = [c for c in ["brix_pct", "sweetness_index", "fructose_pct", "fermenter_temp_c", "ph"] if c in df.columns]
if not chart_cols:
    chart_cols = list(numeric.columns[:3])
if "tank_id" in df.columns:
    tank = st.selectbox("Preview tank", sorted(df["tank_id"].astype(str).unique()))
    view = df[df["tank_id"].astype(str) == tank]
else:
    view = df
preview_col = st.selectbox("Preview signal", chart_cols, format_func=label_of)
fig = go.Figure()
fig.add_trace(go.Scatter(x=view["timestamp"], y=view[preview_col], name=label_of(preview_col), line=dict(color="#0d9488", width=2.4)))
fig.update_layout(template="plotly_white", height=340, margin=dict(l=40, r=16, t=24, b=32), plot_bgcolor="#f8fffd")
st.plotly_chart(fig, width="stretch")

st.dataframe(df.head(80), width="stretch", hide_index=True)

csv_bytes = df.to_csv(index=False).encode("utf-8")
d1, d2 = st.columns(2)
with d1:
    st.download_button("Download CSV", data=csv_bytes, file_name="corn_sweet_ferment.csv", mime="text/csv")
with d2:
    if st.button("Save for Predict page"):
        dest = DATA_DIR / "corn_sweet_ferment.csv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(dest, index=False)
        st.success(f"Saved {dest}. Open Predict factaroy variable and choose Corn sweet fermentation.")

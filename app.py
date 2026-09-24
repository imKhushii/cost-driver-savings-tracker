"""
Cost Driver Dashboard
=====================
An interactive analytics app that decomposes product cost changes into their
underlying drivers - commodity, freight, currency (FX), vendor negotiation, and
tariff - so Category Management, Finance, and Strategic Sourcing partners can
see *why* landed cost moved and where the negotiation opportunities are.

Run:  streamlit run app.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src import analytics as an  # noqa: E402

# ---------------------------------------------------------------------------
# Page config & styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Cost Driver Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Modern gradient colors - PowerBI inspired
DRIVER_COLORS = {
    "Commodity / Material": "#0066CC",      # Professional Blue
    "Freight": "#FF8C42",                   # Vibrant Orange
    "Currency (FX)": "#2ECC71",             # Fresh Green
    "Vendor / Negotiation": "#E74C3C",      # Bold Red
    "Tariff / Duty": "#9B59B6",             # Deep Purple
}

# Apply custom CSS for modern design
st.markdown("""
<script>
// Force dropdown text to be dark
const observer = new MutationObserver(() => {
    const dropdownOptions = document.querySelectorAll('[data-baseweb="listbox"] li, [data-baseweb="menu"] li');
    dropdownOptions.forEach(option => {
        option.style.color = '#1a1a2e';
        option.style.backgroundColor = '#ffffff';
    });
});

observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: false
});
</script>

<style>
    /* Remove conflicting styles - let Streamlit theme handle basics */
    
    body, [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #f8fafc 0%, #eef3f9 50%, #e6eef7 100%) !important;
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #eef3f9 100%) !important;
    }
    
    /* Typography */
    h1, h2, h3, h4 {
        color: #1a1a2e !important;
        font-weight: 700 !important;
    }
    
    label, .stLabel {
        color: #1a1a2e !important;
        font-weight: 500 !important;
    }
    
    /* Form inputs - let them stay white for readability */
    .stSelectbox [data-baseweb="select"],
    .stMultiSelect [data-baseweb="select"],
    input, select, textarea {
        background: #ffffff !important;
        color: #1a1a2e !important;
        border: 2px solid #0066CC !important;
        border-radius: 6px !important;
    }
    
    .stSelectbox [data-baseweb="select"] input,
    .stMultiSelect [data-baseweb="select"] input {
        color: #1a1a2e !important;
    }
    
    /* Dropdown menu styling */
    [data-baseweb="listbox"] li {
        color: #1a1a2e !important;
        background: #ffffff !important;
    }
    
    [data-baseweb="listbox"] li:hover {
        background: #e8f0ff !important;
        color: #0066CC !important;
    }
    
    [data-baseweb="menu"] {
        background: #ffffff !important;
    }
    
    [data-baseweb="menu"] li {
        color: #1a1a2e !important;
        background: #ffffff !important;
    }
    
    [data-baseweb="menu"] li:hover {
        background: #e8f0ff !important;
        color: #0066CC !important;
    }
    
    /* KPI Cards with gradient */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, rgba(0, 102, 204, 0.15) 0%, rgba(46, 204, 113, 0.15) 100%) !important;
        padding: 20px !important;
        border-radius: 12px !important;
        border-left: 4px solid #0066CC !important;
        box-shadow: 0 8px 32px rgba(0, 102, 204, 0.1) !important;
    }
    
    /* Chart containers */
    .stPlotlyChart {
        background: rgba(255, 255, 255, 0.7) !important;
        border-radius: 12px !important;
        padding: 20px !important;
        border: 1px solid rgba(0, 102, 204, 0.2) !important;
    }
    
    /* Data frame */
    .stDataFrame {
        background: rgba(255, 255, 255, 0.8) !important;
        border-radius: 12px !important;
    }
    
    /* Expandable sections */
    .stExpander {
        background: rgba(255, 255, 255, 0.6) !important;
        border-radius: 8px !important;
        border: 1px solid rgba(0, 102, 204, 0.2) !important;
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #0066CC 0%, #004499 100%) !important;
        color: #fff !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 16px rgba(0, 102, 204, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)


def money(x: float) -> str:
    """Format a number as compact USD with color coding."""
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1_000_000:
        return f"{sign}${x/1_000_000:.2f}M"
    if x >= 1_000:
        return f"{sign}${x/1_000:.1f}K"
    return f"{sign}${x:,.0f}"


@st.cache_data
def get_data() -> pd.DataFrame:
    return an.load_data()


# ---------------------------------------------------------------------------
# Load data (with a friendly message if it hasn't been generated yet)
# ---------------------------------------------------------------------------
try:
    df_all = get_data()
except FileNotFoundError as e:
    st.error(str(e))
    st.stop()

periods = an.ordered_periods(df_all)

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.title("📊 Cost Driver Dashboard")
st.sidebar.caption("Sourcing Advisory Analytics")

st.sidebar.markdown("""
<style>
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #1a1a2e !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: #1a1a2e !important;
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.subheader("Comparison window")
default_start = periods[0]
default_end = periods[-1]
start_period = st.sidebar.selectbox("From period", periods, index=0)
end_options = [p for p in periods]
end_period = st.sidebar.selectbox(
    "To period", end_options, index=len(end_options) - 1)

if periods.index(end_period) <= periods.index(start_period):
    st.sidebar.warning("'To' period should be after 'From' period for a change view.")

st.sidebar.subheader("Filters")
categories = st.sidebar.multiselect(
    "Category", sorted(df_all["category"].unique()))
vendors = st.sidebar.multiselect(
    "Vendor", sorted(df_all["vendor"].unique()))
commodities = st.sidebar.multiselect(
    "Commodity", sorted(df_all["commodity"].unique()))

df = an.apply_filters(df_all, categories, vendors, commodities)

if df.empty:
    st.warning("No data matches the selected filters. Adjust and try again.")
    st.stop()

# ---------------------------------------------------------------------------
# Header + KPI row
# ---------------------------------------------------------------------------
st.markdown("### 📊 Product Cost Driver Analysis")
st.markdown(f"""
<div style="
    background: linear-gradient(90deg, rgba(0, 102, 204, 0.1) 0%, rgba(46, 204, 113, 0.1) 100%);
    padding: 15px 20px;
    border-radius: 8px;
    border-left: 4px solid #0066CC;
    margin-bottom: 30px;
">
    <p style="margin: 0; color: #5a6a7a; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">
        📈 Analysis Period: <strong>{start_period}</strong> → <strong>{end_period}</strong> 
        | {df['sku'].nunique()} SKUs | {df['vendor'].nunique()} Vendors | {df['category'].nunique()} Categories
    </p>
</div>
""", unsafe_allow_html=True)

k = an.kpis(df, start_period, end_period)

# Enhanced KPI metrics with gradient backgrounds
col1, col2, col3, col4 = st.columns(4, gap="medium")

with col1:
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(0, 102, 204, 0.15) 0%, rgba(0, 102, 204, 0.05) 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #0066CC;
        text-align: center;
    ">
        <p style="margin: 0; color: #5a6a7a; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Total Cost ({start_period})</p>
        <p style="margin: 10px 0 0 0; color: #0066CC; font-size: 26px; font-weight: 700;">{money(k['start_total'])}</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(46, 204, 113, 0.15) 0%, rgba(46, 204, 113, 0.05) 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #2ECC71;
        text-align: center;
    ">
        <p style="margin: 0; color: #5a6a7a; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Total Cost ({end_period})</p>
        <p style="margin: 10px 0 0 0; color: #2ECC71; font-size: 26px; font-weight: 700;">{money(k['end_total'])}</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    delta_color = "#E74C3C" if k['change'] > 0 else "#2ECC71"
    delta_icon = "📈" if k['change'] > 0 else "📉"
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(231, 76, 60, 0.15) 0%, rgba(231, 76, 60, 0.05) 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #E74C3C;
        text-align: center;
    ">
        <p style="margin: 0; color: #5a6a7a; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Cost Change</p>
        <p style="margin: 10px 0 0 0; color: {delta_color}; font-size: 26px; font-weight: 700;">{delta_icon} {money(k['change'])}</p>
        <p style="margin: 5px 0 0 0; color: #666; font-size: 12px;">{k['pct_change']:+.1f}%</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, rgba(155, 89, 182, 0.15) 0%, rgba(155, 89, 182, 0.05) 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #9B59B6;
        text-align: center;
    ">
        <p style="margin: 0; color: #5a6a7a; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Vendor-Driven (Addressable)</p>
        <p style="margin: 10px 0 0 0; color: #9B59B6; font-size: 26px; font-weight: 700;">{money(k['vendor_driven'])}</p>
        <p style="margin: 5px 0 0 0; color: #666; font-size: 11px;">Negotiation opportunity</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ---------------------------------------------------------------------------
# Waterfall: the flagship view
# ---------------------------------------------------------------------------
st.markdown("### 💧 Cost Change Waterfall")
st.markdown("<p style='color: #5a6a7a; font-size: 13px; margin-bottom: 20px;'>How did total landed cost move, and which drivers caused it?</p>", unsafe_allow_html=True)

wf = an.waterfall_decomposition(df, start_period, end_period)
measure = ["absolute"] + ["relative"] * (len(wf) - 2) + ["total"]

fig_wf = go.Figure(go.Waterfall(
    orientation="v",
    measure=measure,
    x=wf["label"].tolist(),
    y=wf["value"].tolist(),
    text=[money(v) for v in wf["value"]],
    textposition="outside",
    connector={"line": {"color": "rgba(0, 0, 0, 0.15)"}},
    increasing={"marker": {"color": "#E74C3C"}},   # cost up = red
    decreasing={"marker": {"color": "#2ECC71"}},   # cost down = green
    totals={"marker": {"color": "#0066CC"}},
))

fig_wf.update_layout(
    height=500,
    margin=dict(t=20, b=20, l=50, r=20),
    yaxis_title="Extended Cost (USD)",
    xaxis_title="",
    showlegend=False,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0.05)",
    font=dict(color="#1a1a2e", family="Arial"),
    yaxis=dict(gridcolor="rgba(0, 0, 0, 0.08)"),
)

st.plotly_chart(fig_wf, use_container_width=True, config={"displayModeBar": True})

# ---------------------------------------------------------------------------
# Two-column: trend + category breakdown
# ---------------------------------------------------------------------------
left, right = st.columns(2, gap="medium")

with left:
    st.markdown("### 📈 Cost Composition Over Time")
    st.markdown("<p style='color: #5a6a7a; font-size: 13px;'>Stacked driver contribution each quarter.</p>", unsafe_allow_html=True)
    trend = an.driver_trend(df)
    fig_trend = px.area(
        trend, x="period", y="cost", color="driver",
        color_discrete_map=DRIVER_COLORS,
        category_orders={"period": periods},
    )
    fig_trend.update_layout(
        height=450,
        margin=dict(t=10, b=20, l=50, r=20),
        yaxis_title="Extended Cost (USD)",
        xaxis_title="",
        legend_title="",
        legend=dict(orientation="v", x=1.02, y=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0.05)",
        font=dict(color="#1a1a2e", family="Arial"),
        yaxis=dict(gridcolor="rgba(0, 0, 0, 0.08)"),
        hovermode="x unified",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

with right:
    st.markdown("### 🎯 Driver Impact by Category")
    st.markdown(f"<p style='color: #5a6a7a; font-size: 13px;'>Cost change by category, {start_period} → {end_period}.</p>", unsafe_allow_html=True)
    cat = an.category_driver_breakdown(df, start_period, end_period)
    fig_cat = px.bar(
        cat, x="delta", y="category", color="driver", orientation="h",
        color_discrete_map=DRIVER_COLORS,
    )
    fig_cat.update_layout(
        height=450,
        margin=dict(t=10, b=20, l=120, r=20),
        xaxis_title="Cost Change (USD)",
        yaxis_title="",
        legend_title="",
        legend=dict(orientation="v", x=1.02, y=1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0.05)",
        font=dict(color="#1a1a2e", family="Arial"),
        xaxis=dict(gridcolor="rgba(0, 0, 0, 0.08)"),
        barmode="relative",
        hovermode="y unified",
    )
    st.plotly_chart(fig_cat, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Vendor opportunity table
# ---------------------------------------------------------------------------
st.markdown("### 🎯 Vendor Cost Change & Negotiation Opportunity")
st.markdown("""
<p style='color: #5a6a7a; font-size: 13px; margin-bottom: 20px;'>
Vendors ranked by total cost increase. <strong style='color: #E74C3C;'>Vendor-Driven Change</strong> isolates increases not explained by commodity/freight/FX - the strongest negotiation targets.
</p>
""", unsafe_allow_html=True)

vend = an.vendor_opportunity(df, start_period, end_period)
vend_display = vend.rename(columns={
    "vendor": "Vendor",
    "total_cost_start": f"Cost {start_period}",
    "total_cost_end": f"Cost {end_period}",
    "total_change": "Total Change",
    "pct_change": "% Change",
    "vendor_driven_change": "Vendor-Driven Change",
})

# Format with color-coded styling
def color_delta(val):
    """Color-code deltas: red for increase, green for decrease."""
    if isinstance(val, (int, float)):
        if val > 0:
            return 'color: #E74C3C; font-weight: 600;'
        elif val < 0:
            return 'color: #2ECC71; font-weight: 600;'
    return 'color: #1a1a2e;'

styled = vend_display.style.format({
    f"Cost {start_period}": lambda v: money(v),
    f"Cost {end_period}": lambda v: money(v),
    "Total Change": lambda v: money(v),
    "% Change": "{:+.1f}%",
    "Vendor-Driven Change": lambda v: money(v),
}).map(lambda v: color_delta(v) if isinstance(v, (int, float)) else '', subset=["Total Change", "Vendor-Driven Change"])

st.dataframe(styled, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Detail data + export
# ---------------------------------------------------------------------------
st.markdown("---")

with st.expander("🔍 View & export underlying SKU-level data", expanded=False):
    detail_cols = [
        "period", "sku", "product_name", "category", "commodity", "vendor",
        "currency", "units", "unit_cost", "extended_cost",
    ]
    detail = df[detail_cols].sort_values(["period", "category", "vendor"])
    
    st.markdown(f"<p style='color: #5a6a7a; font-size: 12px; margin-bottom: 15px;'><strong>{len(detail)}</strong> SKU-level records across selected filters</p>", unsafe_allow_html=True)
    
    st.dataframe(detail, use_container_width=True, hide_index=True)
    st.download_button(
        "📥 Download filtered data (CSV)",
        data=detail.to_csv(index=False).encode("utf-8"),
        file_name="cost_driver_detail.csv",
        mime="text/csv",
    )

st.markdown("---")
st.markdown("""
<p style='
    color: #666;
    font-size: 12px;
    text-align: center;
    padding-top: 20px;
    opacity: 0.7;
'>
    ✨ Demo built on synthetic data. Replace <code>data/cost_facts.csv</code> with real cost records (same schema) to run against production data.
</p>
""", unsafe_allow_html=True)

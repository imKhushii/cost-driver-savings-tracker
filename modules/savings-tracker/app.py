"""
Savings & Negotiation Tracker
=============================
A governed repository of sourcing savings initiatives. Tracks every negotiation
from identification through realized savings, measures the realization rate
(did promised savings actually land?), and keeps an audit trail of changes.

Run:  streamlit run app.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src import db as _db            # noqa: E402
from src import repository as repo    # noqa: E402
from src import analytics as an       # noqa: E402
from src.constants import (            # noqa: E402
    STATUSES, SAVINGS_TYPES, CONFIDENCE_LEVELS, CURRENCIES,
)

st.set_page_config(
    page_title="Savings & Negotiation Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

STATUS_COLORS = {
    "Identified": "#A6A6A6",
    "In Negotiation": "#2E75B6",
    "Agreed": "#ED7D31",
    "Implemented": "#7030A0",
    "Realized": "#107C41",
    "Cancelled": "#C00000",
}


def money(x: float) -> str:
    if x is None or pd.isna(x):
        return "-"
    sign = "-" if x < 0 else ""
    x = abs(x)
    if x >= 1_000_000:
        return f"{sign}${x/1_000_000:.2f}M"
    if x >= 1_000:
        return f"{sign}${x/1_000:.1f}K"
    return f"{sign}${x:,.0f}"


def ensure_db() -> None:
    """Make sure the database exists; if not, seed it on first run."""
    if not _db.db_exists():
        _db.init_db()
        try:
            from data.seed_data import main as seed_main
            seed_main(reset=False)
            st.toast("Initialised and seeded a fresh database.")
        except Exception:  # noqa: BLE001
            st.warning("Database initialised (empty). Add initiatives to begin.")


ensure_db()


# ===========================================================================
# Sidebar navigation
# ===========================================================================
st.sidebar.title("💰 Savings Tracker")
st.sidebar.caption("Sourcing Negotiation Repository")
page = st.sidebar.radio(
    "Navigate",
    ["📊 Dashboard", "📝 Manage Initiatives", "🕓 Audit Log"],
    label_visibility="collapsed",
)


def load_df() -> pd.DataFrame:
    return repo.list_initiatives()


# ===========================================================================
# PAGE 1 - DASHBOARD
# ===========================================================================
def render_dashboard() -> None:
    df = load_df()
    if df.empty:
        st.info("No initiatives yet. Add some on the **Manage Initiatives** page.")
        return

    # Filters
    with st.sidebar:
        st.subheader("Filters")
        f_status = st.multiselect("Status", STATUSES)
        f_cat = st.multiselect("Category", sorted(df["category"].unique()))
        f_vendor = st.multiselect("Vendor", sorted(df["vendor"].unique()))
        f_owner = st.multiselect("Owner", sorted(df["owner"].unique()))

    view = df.copy()
    if f_status:
        view = view[view["status"].isin(f_status)]
    if f_cat:
        view = view[view["category"].isin(f_cat)]
    if f_vendor:
        view = view[view["vendor"].isin(f_vendor)]
    if f_owner:
        view = view[view["owner"].isin(f_owner)]

    if view.empty:
        st.warning("No initiatives match the selected filters.")
        return

    st.title("Savings Pipeline & Realization")
    st.caption(
        f"{len(view)} initiatives · "
        f"{view['vendor'].nunique()} vendors · "
        f"{view['category'].nunique()} categories")

    k = an.kpis(view)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Projected Savings", money(k["projected"]))
    c2.metric("Realized Savings", money(k["realized"]))
    rr = k["realization_rate"]
    c3.metric("Realization Rate", "-" if pd.isna(rr) else f"{rr*100:.0f}%")
    c4.metric("In-Flight (Pipeline)", money(k["in_flight"]))
    c5.metric("At-Risk (Overdue)", k["at_risk"],
              help="Non-terminal initiatives past their target close date.")

    st.divider()

    # Row: funnel + realized trend
    left, right = st.columns(2)
    with left:
        st.subheader("Pipeline by Status")
        sb = an.savings_by_status(view)
        sb["status"] = pd.Categorical(sb["status"], categories=STATUSES, ordered=True)
        sb = sb.sort_values("status")
        fig = px.bar(
            sb, x="projected_savings", y="status", orientation="h",
            color="status", color_discrete_map=STATUS_COLORS,
            text=sb["projected_savings"].map(money),
        )
        fig.update_layout(
            height=360, showlegend=False, margin=dict(t=20, b=20, l=10, r=10),
            xaxis_title="Projected Savings (USD)", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Realized Savings Over Time")
        trend = an.realized_trend(view)
        if trend.empty:
            st.info("No realized savings recorded yet.")
        else:
            fig = px.bar(trend, x="period", y="realized_savings",
                         text=trend["realized_savings"].map(money))
            fig.update_traces(marker_color="#107C41")
            fig.update_layout(
                height=360, margin=dict(t=20, b=20, l=10, r=10),
                xaxis_title="", yaxis_title="Realized Savings (USD)")
            st.plotly_chart(fig, use_container_width=True)

    # Row: by category + projected vs realized by owner
    left2, right2 = st.columns(2)
    with left2:
        st.subheader("Projected vs Realized by Category")
        cat = an.savings_by_dimension(view, "category")
        fig = go.Figure()
        fig.add_bar(x=cat["category"], y=cat["projected_savings"],
                    name="Projected", marker_color="#2E75B6")
        fig.add_bar(x=cat["category"], y=cat["realized_savings"],
                    name="Realized", marker_color="#107C41")
        fig.update_layout(
            barmode="group", height=360, margin=dict(t=20, b=20, l=10, r=10),
            yaxis_title="USD", legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig, use_container_width=True)

    with right2:
        st.subheader("Realization Rate by Owner")
        own = an.realization_by_owner(view)
        own["rate_pct"] = own["realization_rate"] * 100
        fig = px.bar(own, x="owner", y="rate_pct",
                     text=own["rate_pct"].map(lambda v: f"{v:.0f}%" if pd.notna(v) else "-"))
        fig.update_traces(marker_color="#1F4E79")
        fig.update_layout(
            height=360, margin=dict(t=20, b=20, l=10, r=10),
            xaxis_title="", yaxis_title="Realization Rate (%)")
        st.plotly_chart(fig, use_container_width=True)

    # At-risk watch-list
    st.divider()
    st.subheader("⚠️ At-Risk Watch-List (Overdue, Not Closed)")
    risk = an.at_risk_initiatives(view)
    if risk.empty:
        st.success("No overdue initiatives. Pipeline is on track.")
    else:
        cols = ["id", "initiative_name", "category", "vendor", "owner",
                "status", "target_close_date", "days_overdue", "projected_savings"]
        show = risk[cols].sort_values("days_overdue", ascending=False).copy()
        show["projected_savings"] = show["projected_savings"].map(money)
        st.dataframe(show, use_container_width=True, hide_index=True)

    # Detail + export
    with st.expander("🔍 View & export all initiatives"):
        detail_cols = [
            "id", "initiative_name", "category", "vendor", "owner",
            "savings_type", "status", "baseline_unit_cost",
            "negotiated_unit_cost", "annual_volume", "projected_savings",
            "realized_savings", "realization_rate", "start_date",
            "target_close_date", "realized_date",
        ]
        st.dataframe(view[detail_cols], use_container_width=True, hide_index=True)
        st.download_button(
            "Download filtered initiatives (CSV)",
            data=view[detail_cols].to_csv(index=False).encode("utf-8"),
            file_name="savings_initiatives.csv", mime="text/csv")


# ===========================================================================
# PAGE 2 - MANAGE (CRUD)
# ===========================================================================
def render_manage() -> None:
    st.title("Manage Initiatives")
    tab_add, tab_edit = st.tabs(["➕ Add New", "✏️ Edit / Update / Delete"])

    # ---- Add ----
    with tab_add:
        st.caption("Create a new savings initiative.")
        with st.form("add_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Initiative name *")
            category = c2.text_input("Category *")
            vendor = c3.text_input("Vendor *")

            c4, c5, c6 = st.columns(3)
            owner = c4.text_input("Owner (analyst/buyer) *")
            savings_type = c5.selectbox("Savings type *", SAVINGS_TYPES)
            currency = c6.selectbox("Currency", CURRENCIES)

            c7, c8, c9 = st.columns(3)
            baseline = c7.number_input("Baseline unit cost *", min_value=0.0,
                                       step=0.5, format="%.2f")
            negotiated = c8.number_input("Negotiated unit cost *", min_value=0.0,
                                         step=0.5, format="%.2f")
            volume = c9.number_input("Annual volume (units) *", min_value=0,
                                     step=100)

            c10, c11, c12 = st.columns(3)
            status = c10.selectbox("Status", STATUSES)
            confidence = c11.selectbox("Confidence", CONFIDENCE_LEVELS, index=1)
            realized = c12.number_input("Realized savings (if any)",
                                        min_value=0.0, step=100.0, format="%.2f")

            c13, c14, c15 = st.columns(3)
            start_date = c13.date_input("Start date")
            target_close = c14.date_input("Target close date")
            realized_date = c15.date_input("Realized date (optional)", value=None)

            notes = st.text_area("Notes", "")

            projected_preview = (baseline - negotiated) * volume
            st.info(f"Projected annual savings: **{money(projected_preview)}**")

            submitted = st.form_submit_button("Create initiative", type="primary")
            if submitted:
                data = {
                    "initiative_name": name, "category": category,
                    "vendor": vendor, "owner": owner,
                    "savings_type": savings_type, "currency": currency,
                    "baseline_unit_cost": baseline,
                    "negotiated_unit_cost": negotiated,
                    "annual_volume": int(volume),
                    "realized_savings": realized, "confidence": confidence,
                    "status": status,
                    "start_date": start_date.isoformat(),
                    "target_close_date": target_close.isoformat(),
                    "realized_date": realized_date.isoformat() if realized_date else None,
                    "notes": notes,
                }
                errors = repo.validate(data)
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    new_id = repo.create_initiative(data, changed_by="ui")
                    st.success(f"Created initiative #{new_id}: {name}")

    # ---- Edit ----
    with tab_edit:
        df = load_df()
        if df.empty:
            st.info("No initiatives to edit yet.")
            return
        options = {
            f"#{r.id} · {r.initiative_name} ({r.status})": int(r.id)
            for r in df.itertuples()
        }
        chosen = st.selectbox("Select an initiative", list(options.keys()))
        iid = options[chosen]
        row = repo.get_initiative(iid)

        with st.form("edit_form"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Initiative name", row["initiative_name"])
            category = c2.text_input("Category", row["category"])
            vendor = c3.text_input("Vendor", row["vendor"])

            c4, c5, c6 = st.columns(3)
            owner = c4.text_input("Owner", row["owner"])
            savings_type = c5.selectbox(
                "Savings type", SAVINGS_TYPES,
                index=SAVINGS_TYPES.index(row["savings_type"])
                if row["savings_type"] in SAVINGS_TYPES else 0)
            status = c6.selectbox(
                "Status", STATUSES, index=STATUSES.index(row["status"]))

            c7, c8, c9 = st.columns(3)
            baseline = c7.number_input("Baseline unit cost", min_value=0.0,
                                       value=float(row["baseline_unit_cost"]),
                                       step=0.5, format="%.2f")
            negotiated = c8.number_input("Negotiated unit cost", min_value=0.0,
                                         value=float(row["negotiated_unit_cost"]),
                                         step=0.5, format="%.2f")
            volume = c9.number_input("Annual volume", min_value=0,
                                     value=int(row["annual_volume"]), step=100)

            c10, c11 = st.columns(2)
            realized = c10.number_input(
                "Realized savings", min_value=0.0,
                value=float(row["realized_savings"]), step=100.0, format="%.2f")
            confidence = c11.selectbox(
                "Confidence", CONFIDENCE_LEVELS,
                index=CONFIDENCE_LEVELS.index(row["confidence"])
                if row["confidence"] in CONFIDENCE_LEVELS else 1)

            c12, c13 = st.columns(2)
            realized_date_val = (
                pd.to_datetime(row["realized_date"]).date()
                if row["realized_date"] else None)
            target_val = (
                pd.to_datetime(row["target_close_date"]).date()
                if row["target_close_date"] else None)
            target_close = c12.date_input("Target close date", value=target_val)
            realized_date = c13.date_input("Realized date", value=realized_date_val)

            notes = st.text_area("Notes", row.get("notes") or "")

            proj = (baseline - negotiated) * volume
            st.info(f"Projected annual savings: **{money(proj)}**  ·  "
                    f"Current realization: "
                    f"{(realized/proj*100) if proj else 0:.0f}%")

            save = st.form_submit_button("💾 Save changes", type="primary")

        if save:
            updates = {
                "initiative_name": name, "category": category, "vendor": vendor,
                "owner": owner, "savings_type": savings_type, "status": status,
                "baseline_unit_cost": baseline,
                "negotiated_unit_cost": negotiated, "annual_volume": int(volume),
                "realized_savings": realized, "confidence": confidence,
                "target_close_date": target_close.isoformat() if target_close else None,
                "realized_date": realized_date.isoformat() if realized_date else None,
                "notes": notes,
            }
            errors = repo.validate(dict(row, **updates))
            if errors:
                for e in errors:
                    st.error(e)
            else:
                n = repo.update_initiative(iid, updates, changed_by="ui")
                if n:
                    st.success(f"Saved {n} change(s) to initiative #{iid}.")
                else:
                    st.info("No changes detected.")

        with st.expander("🗑️ Delete this initiative"):
            st.warning("Deleting is permanent and removes its audit history.")
            if st.button(f"Delete initiative #{iid}", type="secondary"):
                repo.delete_initiative(iid)
                st.success(f"Deleted initiative #{iid}. Reselect above.")


# ===========================================================================
# PAGE 3 - AUDIT LOG
# ===========================================================================
def render_audit() -> None:
    st.title("Audit Log")
    st.caption("Append-only history of every change, for data governance.")
    log = repo.get_audit_log()
    if log.empty:
        st.info("No audit entries yet.")
        return
    df = load_df()
    name_map = dict(zip(df["id"], df["initiative_name"])) if not df.empty else {}
    log["initiative"] = log["initiative_id"].map(
        lambda i: name_map.get(i, f"#{i} (deleted)"))
    show = log[["changed_at", "initiative", "field_changed", "old_value",
                "new_value", "changed_by"]]
    st.dataframe(show, use_container_width=True, hide_index=True)
    st.download_button(
        "Download audit log (CSV)",
        data=show.to_csv(index=False).encode("utf-8"),
        file_name="audit_log.csv", mime="text/csv")


# ===========================================================================
# Router
# ===========================================================================
if page.startswith("📊"):
    render_dashboard()
elif page.startswith("📝"):
    render_manage()
else:
    render_audit()

st.sidebar.divider()
st.sidebar.caption(
    "Demo on synthetic data (SQLite). Reset any time with "
    "`python data/seed_data.py`.")

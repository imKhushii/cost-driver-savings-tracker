"""
Analytics for the Savings Tracker.

Pure functions over the initiatives DataFrame (as returned by
`repository.list_initiatives`) that produce the aggregates the dashboard renders.
Keeping them UI-free makes them unit-testable.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .constants import TERMINAL_STATUSES


def _period_from_date(series: pd.Series) -> pd.Series:
    """Map an ISO date column to a 'YYYY-Qn' fiscal quarter label."""
    dt = pd.to_datetime(series, errors="coerce")
    q = dt.dt.quarter
    return dt.dt.year.astype("Int64").astype(str) + "-Q" + q.astype("Int64").astype(str)


def kpis(df: pd.DataFrame) -> dict:
    """Headline savings KPIs across the (already filtered) initiatives."""
    if df.empty:
        return {
            "count": 0, "projected": 0.0, "realized": 0.0,
            "realization_rate": float("nan"), "in_flight": 0.0, "at_risk": 0,
        }
    projected = float(df["projected_savings"].sum())
    realized = float(df["realized_savings"].sum())
    # In-flight = projected savings not yet in a terminal (Realized/Cancelled) state.
    in_flight_mask = ~df["status"].isin(TERMINAL_STATUSES)
    in_flight = float(df.loc[in_flight_mask, "projected_savings"].sum())
    return {
        "count": int(len(df)),
        "projected": projected,
        "realized": realized,
        "realization_rate": (realized / projected) if projected else float("nan"),
        "in_flight": in_flight,
        "at_risk": int(at_risk_initiatives(df).shape[0]),
    }


def savings_by_status(df: pd.DataFrame) -> pd.DataFrame:
    """Projected savings and count by status (funnel order preserved by caller)."""
    if df.empty:
        return pd.DataFrame(columns=["status", "projected_savings", "count"])
    g = (
        df.groupby("status")
        .agg(projected_savings=("projected_savings", "sum"),
             count=("id", "count"))
        .reset_index()
    )
    return g


def savings_by_dimension(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Projected vs realized savings grouped by an arbitrary dimension column."""
    if df.empty:
        return pd.DataFrame(columns=[dimension, "projected_savings", "realized_savings"])
    g = (
        df.groupby(dimension)
        .agg(projected_savings=("projected_savings", "sum"),
             realized_savings=("realized_savings", "sum"),
             count=("id", "count"))
        .reset_index()
        .sort_values("projected_savings", ascending=False)
    )
    return g


def realized_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Realized savings by the fiscal quarter in which they landed."""
    realized = df[(df["realized_savings"] > 0) & df["realized_date"].notna()].copy()
    if realized.empty:
        return pd.DataFrame(columns=["period", "realized_savings"])
    realized["period"] = _period_from_date(realized["realized_date"])
    g = (
        realized.groupby("period")["realized_savings"].sum().reset_index()
        .sort_values("period")
    )
    return g


def at_risk_initiatives(df: pd.DataFrame) -> pd.DataFrame:
    """
    Non-terminal initiatives whose target close date has passed - the governance
    watch-list (savings promised but not yet landed and overdue).
    """
    if df.empty:
        return df
    today = pd.Timestamp.today().normalize()
    target = pd.to_datetime(df["target_close_date"], errors="coerce")
    mask = (
        (~df["status"].isin(TERMINAL_STATUSES))
        & target.notna()
        & (target < today)
    )
    out = df.loc[mask].copy()
    if not out.empty:
        out["days_overdue"] = (today - target[mask]).dt.days
    return out


def realization_by_owner(df: pd.DataFrame) -> pd.DataFrame:
    """Projected, realized and realization rate by initiative owner."""
    if df.empty:
        return pd.DataFrame(
            columns=["owner", "projected_savings", "realized_savings",
                     "realization_rate"])
    g = (
        df.groupby("owner")
        .agg(projected_savings=("projected_savings", "sum"),
             realized_savings=("realized_savings", "sum"),
             count=("id", "count"))
        .reset_index()
    )
    g["realization_rate"] = np.where(
        g["projected_savings"] > 0,
        g["realized_savings"] / g["projected_savings"],
        np.nan,
    )
    return g.sort_values("projected_savings", ascending=False)

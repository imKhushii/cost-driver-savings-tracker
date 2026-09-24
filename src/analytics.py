"""
Analytics engine for the Cost Driver Dashboard.

Pure functions that turn the tidy cost fact table into the aggregates the
dashboard renders. Kept UI-free so the logic can be unit-tested independently.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd

# Driver columns, in the order they should appear in the waterfall.
DRIVER_COLUMNS = [
    "material_cost",
    "freight_cost",
    "fx_impact",
    "vendor_cost",
    "tariff_cost",
]

DRIVER_LABELS = {
    "material_cost": "Commodity / Material",
    "freight_cost": "Freight",
    "fx_impact": "Currency (FX)",
    "vendor_cost": "Vendor / Negotiation",
    "tariff_cost": "Tariff / Duty",
}

DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "cost_facts.csv",
)


def load_data(path: str = DATA_FILE) -> pd.DataFrame:
    """Load the cost fact table. Raises a clear error if it is missing."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Data file not found: {path}\n"
            "Generate it first with:  python data/generate_data.py"
        )
    df = pd.read_csv(path)
    # A sortable numeric key for chronological ordering of "YYYY-Qn".
    df["period_order"] = (
        df["period"].str[:4].astype(int) * 10
        + df["period"].str[-1].astype(int)
    )
    return df


def ordered_periods(df: pd.DataFrame) -> list:
    """Return the list of periods in chronological order."""
    return (
        df[["period", "period_order"]]
        .drop_duplicates()
        .sort_values("period_order")["period"]
        .tolist()
    )


def apply_filters(df: pd.DataFrame, categories=None, vendors=None,
                  commodities=None) -> pd.DataFrame:
    """Filter the fact table by the selected dimension members."""
    out = df
    if categories:
        out = out[out["category"].isin(categories)]
    if vendors:
        out = out[out["vendor"].isin(vendors)]
    if commodities:
        out = out[out["commodity"].isin(commodities)]
    return out


def _driver_totals(df: pd.DataFrame) -> pd.Series:
    """Sum each driver's *extended* (unit_cost-weighted) contribution."""
    weighted = df[DRIVER_COLUMNS].multiply(df["units"], axis=0)
    return weighted.sum()


def waterfall_decomposition(df: pd.DataFrame, start_period: str,
                            end_period: str) -> pd.DataFrame:
    """
    Decompose the change in total extended cost between two periods into the
    contribution of each driver.

    Returns a DataFrame with columns: label, value, kind
    where kind is one of {'total', 'driver'} for rendering a waterfall.
    """
    start_df = df[df["period"] == start_period]
    end_df = df[df["period"] == end_period]

    start_total = float((start_df["extended_cost"]).sum())
    end_total = float((end_df["extended_cost"]).sum())

    start_drivers = _driver_totals(start_df)
    end_drivers = _driver_totals(end_df)
    delta = (end_drivers - start_drivers)

    rows = [{"label": f"{start_period}\nTotal Cost",
             "value": start_total, "kind": "total"}]
    for col in DRIVER_COLUMNS:
        rows.append({
            "label": DRIVER_LABELS[col],
            "value": float(delta[col]),
            "kind": "driver",
        })
    rows.append({"label": f"{end_period}\nTotal Cost",
                 "value": end_total, "kind": "total"})
    return pd.DataFrame(rows)


def driver_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Extended cost per driver per period (long form) for a stacked area chart."""
    weighted = df.copy()
    for col in DRIVER_COLUMNS:
        weighted[col] = weighted[col] * weighted["units"]
    grouped = (
        weighted.groupby(["period", "period_order"])[DRIVER_COLUMNS]
        .sum()
        .reset_index()
        .sort_values("period_order")
    )
    long = grouped.melt(
        id_vars=["period", "period_order"],
        value_vars=DRIVER_COLUMNS,
        var_name="driver",
        value_name="cost",
    )
    long["driver"] = long["driver"].map(DRIVER_LABELS)
    return long


def total_cost_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Total extended cost per period."""
    grouped = (
        df.groupby(["period", "period_order"])["extended_cost"]
        .sum()
        .reset_index()
        .sort_values("period_order")
    )
    return grouped


def category_driver_breakdown(df: pd.DataFrame, start_period: str,
                              end_period: str) -> pd.DataFrame:
    """Per-category change in each driver between two periods (long form)."""
    def weighted_by_cat(period):
        sub = df[df["period"] == period].copy()
        for col in DRIVER_COLUMNS:
            sub[col] = sub[col] * sub["units"]
        return sub.groupby("category")[DRIVER_COLUMNS].sum()

    start = weighted_by_cat(start_period)
    end = weighted_by_cat(end_period)
    delta = (end.subtract(start, fill_value=0)).reset_index()
    long = delta.melt(id_vars="category", value_vars=DRIVER_COLUMNS,
                      var_name="driver", value_name="delta")
    long["driver"] = long["driver"].map(DRIVER_LABELS)
    return long


def vendor_opportunity(df: pd.DataFrame, start_period: str,
                       end_period: str) -> pd.DataFrame:
    """
    Rank vendors by total extended cost change between two periods, and isolate
    the *vendor-driven* portion (the negotiation opportunity) - the change in
    vendor pricing that is not explained by commodity/freight/FX movement.
    """
    work = df.copy()
    work["vendor_cost_ext"] = work["vendor_cost"] * work["units"]

    def agg(period: str) -> pd.DataFrame:
        sub = work[work["period"] == period]
        return sub.groupby("vendor").agg(
            total_cost=("extended_cost", "sum"),
            vendor_ext=("vendor_cost_ext", "sum"),
        )

    start = agg(start_period)
    end = agg(end_period)
    joined = start.join(end, lsuffix="_start", rsuffix="_end", how="outer").fillna(0)
    joined["total_change"] = joined["total_cost_end"] - joined["total_cost_start"]
    joined["pct_change"] = np.where(
        joined["total_cost_start"] != 0,
        joined["total_change"] / joined["total_cost_start"] * 100,
        np.nan,
    )
    joined["vendor_driven_change"] = joined["vendor_ext_end"] - joined["vendor_ext_start"]
    out = (
        joined[["total_cost_start", "total_cost_end", "total_change",
                "pct_change", "vendor_driven_change"]]
        .sort_values("total_change", ascending=False)
        .reset_index()
    )
    return out


def kpis(df: pd.DataFrame, start_period: str, end_period: str) -> dict:
    """Headline KPIs for the selected window."""
    start_total = float(df[df["period"] == start_period]["extended_cost"].sum())
    end_total = float(df[df["period"] == end_period]["extended_cost"].sum())
    change = end_total - start_total
    pct = (change / start_total * 100) if start_total else float("nan")

    # Vendor-driven change = the negotiation-addressable slice.
    vendor = vendor_opportunity(df, start_period, end_period)
    vendor_driven = float(vendor["vendor_driven_change"].sum())

    return {
        "start_total": start_total,
        "end_total": end_total,
        "change": change,
        "pct_change": pct,
        "vendor_driven": vendor_driven,
    }

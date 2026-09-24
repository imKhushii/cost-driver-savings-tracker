"""
Export a Power BI-ready star schema from the cost fact table.

Power BI Desktop is Windows-only, so instead of shipping a binary .pbix this
script produces clean, import-ready CSVs modelled as a proper star schema:

    Fact:
        FactCostDriver   grain = period x SKU x driver (unpivoted, tidy)

    Dimensions:
        DimPeriod        one row per fiscal quarter (with a real Date for time-intel)
        DimProduct       one row per SKU
        DimVendor        one row per vendor
        DimDriver        one row per cost driver (with display sort order)

    Helper (disconnected) tables for the change/waterfall slicers:
        DimStartPeriod, DimEndPeriod

Unpivoting the drivers into FactCostDriver is deliberate: it lets a single
Power BI Waterfall/《stacked》 visual pivot on the driver, and keeps every measure
as a simple SUM - the idiomatic, high-performance Power BI modelling pattern.

Run:  python powerbi/export_star_schema.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODEL_DIR = os.path.join(HERE, "model")
sys.path.insert(0, ROOT)

from src import analytics as an  # noqa: E402

# Quarter -> first calendar day, so Power BI gets a genuine Date column.
QUARTER_START_MONTH = {"Q1": 1, "Q2": 4, "Q3": 7, "Q4": 10}

DRIVER_SORT = {
    "Commodity / Material": 1,
    "Freight": 2,
    "Currency (FX)": 3,
    "Vendor / Negotiation": 4,
    "Tariff / Duty": 5,
}


def build_dim_period(df: pd.DataFrame) -> pd.DataFrame:
    periods = (
        df[["period", "period_order"]].drop_duplicates().sort_values("period_order")
    )
    periods["year"] = periods["period"].str[:4].astype(int)
    periods["quarter"] = periods["period"].str[-2:]
    periods["quarter_num"] = periods["period"].str[-1].astype(int)
    periods["date"] = pd.to_datetime(dict(
        year=periods["year"],
        month=periods["quarter"].map(QUARTER_START_MONTH),
        day=1,
    ))
    periods["quarter_label"] = periods["quarter"] + " " + periods["year"].astype(str)
    return periods[[
        "period", "period_order", "year", "quarter", "quarter_num",
        "quarter_label", "date",
    ]]


def build_dim_product(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df[["sku", "product_name", "category", "commodity", "vendor", "currency"]]
        .drop_duplicates("sku")
        .sort_values("sku")
        .reset_index(drop=True)
    )


def build_dim_vendor(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df[["vendor", "currency"]]
        .drop_duplicates("vendor")
        .sort_values("vendor")
        .reset_index(drop=True)
    )


def build_dim_driver() -> pd.DataFrame:
    return pd.DataFrame(
        [{"driver": name, "sort_order": order} for name, order in DRIVER_SORT.items()]
    )


def build_fact_cost_driver(df: pd.DataFrame) -> pd.DataFrame:
    """Unpivot the wide driver columns into a tidy fact at period x SKU x driver."""
    work = df.copy()
    for col in an.DRIVER_COLUMNS:
        work[col + "_ext"] = work[col] * work["units"]

    ext_cols = [c + "_ext" for c in an.DRIVER_COLUMNS]
    long = work.melt(
        id_vars=["period", "sku", "vendor", "category", "commodity", "units"],
        value_vars=ext_cols,
        var_name="driver_col",
        value_name="cost_ext",
    )
    # Map raw column -> friendly driver label used by DimDriver.
    col_to_label = {c + "_ext": an.DRIVER_LABELS[c] for c in an.DRIVER_COLUMNS}
    long["driver"] = long["driver_col"].map(col_to_label)
    long = long.drop(columns=["driver_col"])
    long["cost_ext"] = long["cost_ext"].round(2)
    return long[[
        "period", "sku", "vendor", "category", "commodity", "driver",
        "units", "cost_ext",
    ]]


def main() -> None:
    os.makedirs(MODEL_DIR, exist_ok=True)
    df = an.load_data()

    dim_period = build_dim_period(df)
    outputs = {
        "DimPeriod.csv": dim_period,
        "DimProduct.csv": build_dim_product(df),
        "DimVendor.csv": build_dim_vendor(df),
        "DimDriver.csv": build_dim_driver(),
        "FactCostDriver.csv": build_fact_cost_driver(df),
        # Disconnected slicer tables for the "compare two periods" waterfall.
        "DimStartPeriod.csv": dim_period[["period", "period_order"]].rename(
            columns={"period": "start_period"}),
        "DimEndPeriod.csv": dim_period[["period", "period_order"]].rename(
            columns={"period": "end_period"}),
    }

    for name, frame in outputs.items():
        path = os.path.join(MODEL_DIR, name)
        frame.to_csv(path, index=False)
        print(f"  wrote {name:24s} {len(frame):>5,} rows")

    print(f"\nStar schema written to {MODEL_DIR}")
    print("Import these CSVs into Power BI (Get Data > Folder or Text/CSV).")


if __name__ == "__main__":
    main()

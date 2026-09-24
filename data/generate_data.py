"""
Synthetic data generator for the Cost Driver Dashboard.

Produces a realistic, tidy fact table where each row is one SKU in one fiscal
quarter, with landed product cost decomposed into its underlying drivers:

    total_cost = material_cost   (commodity index driven)
               + freight_cost    (freight index driven)
               + fx_impact        (currency movement vs. USD)
               + vendor_cost      (vendor pricing / negotiation behavior)
               + tariff_cost      (duty / tariff)

Because every component is stored explicitly, period-over-period cost change
can be exactly decomposed into driver contributions (the waterfall view).

Run:  python data/generate_data.py
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd

SEED = 42
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(DATA_DIR, "cost_facts.csv")

# ---------------------------------------------------------------------------
# Reference / dimension data (automotive aftermarket flavoured)
# ---------------------------------------------------------------------------
CATEGORIES = {
    "Brakes":        {"commodity": "Steel",     "base_cost": 42.0},
    "Batteries":     {"commodity": "Lead",      "base_cost": 118.0},
    "Filters":       {"commodity": "Paper",     "base_cost": 9.5},
    "Motor Oil":     {"commodity": "Crude Oil", "base_cost": 24.0},
    "Wipers":        {"commodity": "Rubber",    "base_cost": 12.0},
    "Belts & Hoses": {"commodity": "Rubber",    "base_cost": 16.5},
    "Radiators":     {"commodity": "Aluminum",  "base_cost": 88.0},
    "Spark Plugs":   {"commodity": "Copper",    "base_cost": 6.0},
}

VENDORS = {
    "Ironclad Auto":      {"currency": "USD", "behavior": "aggressive"},   # raises fast
    "Zhongli Parts":      {"currency": "CNY", "behavior": "aggressive"},
    "EuroTech GmbH":      {"currency": "EUR", "behavior": "fair"},
    "Monterrey Supply":   {"currency": "MXN", "behavior": "fair"},
    "Great Lakes Mfg":    {"currency": "USD", "behavior": "sticky"},       # slow to drop
    "Pacific Components":  {"currency": "CNY", "behavior": "fair"},
}

# Which vendors supply which categories (a vendor can supply several)
VENDOR_CATEGORY = {
    "Ironclad Auto":      ["Brakes", "Radiators", "Spark Plugs"],
    "Zhongli Parts":      ["Filters", "Wipers", "Belts & Hoses", "Spark Plugs"],
    "EuroTech GmbH":      ["Brakes", "Batteries", "Radiators"],
    "Monterrey Supply":   ["Filters", "Motor Oil", "Wipers"],
    "Great Lakes Mfg":    ["Batteries", "Brakes", "Belts & Hoses"],
    "Pacific Components":  ["Filters", "Wipers", "Spark Plugs", "Motor Oil"],
}

# Quarters covered
QUARTERS = [
    "2023-Q1", "2023-Q2", "2023-Q3", "2023-Q4",
    "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4",
    "2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4",
]


def _index_series(rng: np.random.Generator, start: float, drift: float,
                  vol: float, n: int) -> np.ndarray:
    """Random-walk index normalised so the first period == 1.0."""
    steps = rng.normal(loc=drift, scale=vol, size=n)
    level = start * np.cumprod(1 + steps)
    return level / level[0]


def build_reference_series(rng: np.random.Generator) -> dict:
    n = len(QUARTERS)

    commodities = {
        "Steel":     _index_series(rng, 1.0,  0.025, 0.05, n),
        "Lead":      _index_series(rng, 1.0,  0.015, 0.04, n),
        "Paper":     _index_series(rng, 1.0,  0.010, 0.03, n),
        "Crude Oil": _index_series(rng, 1.0,  0.030, 0.09, n),
        "Rubber":    _index_series(rng, 1.0,  0.018, 0.06, n),
        "Aluminum":  _index_series(rng, 1.0,  0.022, 0.05, n),
        "Copper":    _index_series(rng, 1.0,  0.028, 0.06, n),
    }
    commodity_df = pd.DataFrame(commodities, index=QUARTERS)

    freight_df = pd.DataFrame(
        {"freight_index": _index_series(rng, 1.0, 0.020, 0.08, n)},
        index=QUARTERS,
    )

    # FX expressed as "USD cost multiplier" for buying in that currency.
    # >1 means the foreign currency strengthened (parts got more expensive in USD).
    fx = {
        "USD": np.ones(n),
        "EUR": _index_series(rng, 1.0,  0.008, 0.03, n),
        "CNY": _index_series(rng, 1.0,  0.012, 0.025, n),
        "MXN": _index_series(rng, 1.0, -0.005, 0.04, n),
    }
    fx_df = pd.DataFrame(fx, index=QUARTERS)

    return {"commodity": commodity_df, "freight": freight_df, "fx": fx_df}


def _vendor_adjustment_factor(behavior: str, commodity_move: float,
                              rng: np.random.Generator) -> float:
    """
    Models vendor pricing behavior relative to underlying commodity movement.
    Returns a multiplicative adjustment applied on top of pass-through cost.
      - aggressive: raises more than commodities rose, resists drops
      - sticky:     slow to pass savings when commodities fall
      - fair:       roughly tracks commodities
    """
    noise = rng.normal(0, 0.01)
    if behavior == "aggressive":
        # adds ~40% of any up-move, gives back little on down-moves
        extra = 0.4 * max(commodity_move, 0) - 0.1 * min(commodity_move, 0)
        return 1.0 + extra + noise
    if behavior == "sticky":
        extra = 0.15 * max(commodity_move, 0) - 0.6 * min(commodity_move, 0)
        return 1.0 + extra + noise
    # fair
    return 1.0 + 0.05 * max(commodity_move, 0) + noise


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    ref = build_reference_series(rng)
    commodity_df, freight_df, fx_df = ref["commodity"], ref["freight"], ref["fx"]

    # Build the SKU master
    skus = []
    sku_counter = 1000
    for vendor, cats in VENDOR_CATEGORY.items():
        currency = VENDORS[vendor]["currency"]
        behavior = VENDORS[vendor]["behavior"]
        for cat in cats:
            n_skus = rng.integers(2, 5)
            for _ in range(n_skus):
                sku_counter += 1
                skus.append({
                    "sku": f"SKU-{sku_counter}",
                    "product_name": f"{cat} {rng.integers(100, 999)}",
                    "category": cat,
                    "commodity": CATEGORIES[cat]["commodity"],
                    "vendor": vendor,
                    "currency": currency,
                    "behavior": behavior,
                    "base_cost": CATEGORIES[cat]["base_cost"] * rng.uniform(0.8, 1.2),
                    "units": int(rng.integers(500, 20000)),
                    # share of cost that is material vs freight vs tariff
                    "material_share": rng.uniform(0.45, 0.65),
                    "freight_share": rng.uniform(0.10, 0.22),
                    "tariff_rate": rng.choice([0.0, 0.025, 0.05, 0.075]),
                })

    rows = []
    for s in skus:
        base = s["base_cost"]
        material_base = base * s["material_share"]          # local currency
        freight_base = base * s["freight_share"]            # USD (freight billed in USD)
        vendor_base = base * (1 - s["material_share"] - s["freight_share"])  # local
        commodity_start = commodity_df[s["commodity"]].iloc[0]

        for q in QUARTERS:
            c_idx = commodity_df[s["commodity"]].loc[q]
            f_idx = freight_df["freight_index"].loc[q]
            fx_mult = fx_df[s["currency"]].loc[q]

            commodity_move = (c_idx / commodity_start) - 1.0
            vendor_factor = _vendor_adjustment_factor(
                s["behavior"], commodity_move, rng)

            # --- Exactly additive decomposition (all buckets sum to unit_cost) ---
            # Local-currency content before FX conversion:
            local_material = material_base * c_idx           # commodity driver
            local_vendor = vendor_base * vendor_factor       # vendor/negotiation driver
            imported_content = local_material + local_vendor

            material_cost = local_material
            vendor_cost = local_vendor
            freight_cost = freight_base * f_idx
            # FX isolated as its own additive bucket (0 for USD vendors):
            fx_impact = imported_content * (fx_mult - 1.0)
            subtotal = imported_content * fx_mult + freight_cost
            tariff_cost = subtotal * s["tariff_rate"]

            # Round drivers first, then derive unit_cost from them so the
            # decomposition reconciles exactly (no rounding drift in the waterfall).
            material_cost = round(material_cost, 4)
            freight_cost = round(freight_cost, 4)
            fx_impact = round(fx_impact, 4)
            vendor_cost = round(vendor_cost, 4)
            tariff_cost = round(tariff_cost, 4)
            unit_cost = round(material_cost + vendor_cost + fx_impact
                              + freight_cost + tariff_cost, 4)

            rows.append({
                "period": q,
                "sku": s["sku"],
                "product_name": s["product_name"],
                "category": s["category"],
                "commodity": s["commodity"],
                "vendor": s["vendor"],
                "currency": s["currency"],
                "units": s["units"],
                "material_cost": material_cost,
                "freight_cost": freight_cost,
                "fx_impact": fx_impact,
                "vendor_cost": vendor_cost,
                "tariff_cost": tariff_cost,
                "unit_cost": unit_cost,
                "extended_cost": round(unit_cost * s["units"], 2),
            })

    df = pd.DataFrame(rows)
    return df


def main() -> None:
    df = generate()
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Wrote {len(df):,} rows for {df['sku'].nunique()} SKUs "
          f"across {df['period'].nunique()} quarters -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

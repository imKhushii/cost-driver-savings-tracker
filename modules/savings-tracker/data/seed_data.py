"""
Seed the Savings Tracker with a realistic portfolio of negotiation initiatives.

Creates the SQLite database (via the schema), then inserts a diverse set of
initiatives spread across statuses, categories, vendors, owners and savings
types - including some Realized (with partial/full realization) and some overdue
"at-risk" items so every dashboard view has meaningful data.

Run:  python data/seed_data.py
"""
from __future__ import annotations

import os
import sys
from datetime import date, timedelta

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src import db as _db          # noqa: E402
from src import repository as repo  # noqa: E402

SEED = 7

CATEGORIES = {
    "Brakes": "Ironclad Auto",
    "Batteries": "EuroTech GmbH",
    "Filters": "Zhongli Parts",
    "Motor Oil": "Monterrey Supply",
    "Wipers": "Pacific Components",
    "Belts & Hoses": "Great Lakes Mfg",
    "Radiators": "Ironclad Auto",
    "Spark Plugs": "Zhongli Parts",
}
VENDORS = list(set(CATEGORIES.values())) + ["Apex Fasteners", "Delta Rubber Co"]
OWNERS = ["A. Rivera", "S. Kapoor", "J. Chen", "M. O'Neil", "L. Fischer"]
SAVINGS_TYPES = ["Commodity", "Freight", "Payment Terms", "Consolidation",
                 "Resourcing", "Rebate", "Spec Change"]
CONFIDENCE = ["High", "Medium", "Low"]
CURRENCY = "USD"

STATUS_WEIGHTS = {
    "Identified": 0.18,
    "In Negotiation": 0.22,
    "Agreed": 0.15,
    "Implemented": 0.15,
    "Realized": 0.22,
    "Cancelled": 0.08,
}


def _iso(d: date) -> str:
    return d.isoformat()


def build_records(n: int = 40) -> list:
    rng = np.random.default_rng(SEED)
    statuses = list(STATUS_WEIGHTS.keys())
    weights = np.array(list(STATUS_WEIGHTS.values()))
    weights = weights / weights.sum()

    records = []
    today = date.today()
    for i in range(n):
        category = rng.choice(list(CATEGORIES.keys()))
        # Usually the category's primary vendor, sometimes an alternate.
        vendor = (CATEGORIES[category] if rng.random() < 0.7
                  else rng.choice(VENDORS))
        status = rng.choice(statuses, p=weights)

        baseline = float(round(rng.uniform(5, 140), 2))
        savings_pct = rng.uniform(0.02, 0.15)   # 2% - 15% negotiated reduction
        negotiated = float(round(baseline * (1 - savings_pct), 2))
        volume = int(rng.integers(2_000, 120_000))
        projected = (baseline - negotiated) * volume

        start = today - timedelta(days=int(rng.integers(30, 540)))
        target = start + timedelta(days=int(rng.integers(45, 180)))

        realized_savings = 0.0
        realized_date = None
        if status == "Realized":
            # Realization between 70% and 105% of projected (some over/under-deliver).
            rate = rng.uniform(0.70, 1.05)
            realized_savings = round(projected * rate, 2)
            realized_date = _iso(min(
                target + timedelta(days=int(rng.integers(-20, 40))), today))
        elif status == "Implemented":
            # Some savings starting to land (partial).
            realized_savings = round(projected * rng.uniform(0.1, 0.4), 2)

        records.append({
            "initiative_name": f"{category} {savings_pct*100:.0f}% "
                               f"{rng.choice(SAVINGS_TYPES)} - {vendor.split()[0]}",
            "category": category,
            "vendor": vendor,
            "owner": rng.choice(OWNERS),
            "savings_type": rng.choice(SAVINGS_TYPES),
            "currency": CURRENCY,
            "baseline_unit_cost": baseline,
            "negotiated_unit_cost": negotiated,
            "annual_volume": volume,
            "realized_savings": realized_savings,
            "confidence": rng.choice(CONFIDENCE, p=[0.4, 0.4, 0.2]),
            "status": status,
            "start_date": _iso(start),
            "target_close_date": _iso(target),
            "realized_date": realized_date,
            "notes": "",
        })
    return records


def main(reset: bool = True) -> None:
    if reset and os.path.exists(_db.DB_PATH):
        os.remove(_db.DB_PATH)
    _db.init_db()

    records = build_records()
    for r in records:
        errors = repo.validate(r)
        if errors:
            # Skip invalid synthetic rows defensively (should not happen).
            print(f"  skipped invalid record: {errors}")
            continue
        repo.create_initiative(r, changed_by="seed")

    df = repo.list_initiatives()
    print(f"Seeded {len(df)} initiatives into {_db.DB_PATH}")
    print(f"  Projected savings: ${df['projected_savings'].sum():,.0f}")
    print(f"  Realized savings : ${df['realized_savings'].sum():,.0f}")


if __name__ == "__main__":
    main()

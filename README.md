# Cost Driver Dashboard

An interactive analytics application that decomposes **product cost changes** into
their underlying drivers — **commodity/material, freight, currency (FX), vendor
negotiation, and tariff** — so Category Management, Finance, and Strategic Sourcing
partners can see *why* landed cost moved and *where the negotiation opportunities are*.

Built for a **Sourcing Advisory Analyst** portfolio: it demonstrates cost analytics,
opportunity identification, dashboard development, and data governance in one tool.

> The demo runs on realistic **synthetic data**. Swap in real cost records with the
> same schema to run it against production data — no code changes required.

---

## What it shows

| View | Business question it answers |
|------|------------------------------|
| **KPI cards** | How much did total cost change, and how much is *addressable* by negotiation? |
| **Cost Change Waterfall** | Which drivers caused cost to move between two periods? (fully reconciling) |
| **Cost Composition Over Time** | How is spend split across drivers each quarter? |
| **Driver Impact by Category** | Which categories are absorbing the cost pressure, and from what? |
| **Vendor Opportunity Table** | Which vendors raised cost beyond commodity/FX pass-through? |
| **Detail + Export** | SKU-level drill-down with one-click CSV export. |

The waterfall is **exactly additive** — the sum of driver contributions plus the
starting total equals the ending total (verified by an automated test), so the story
you present to leadership is honest and defensible.

---

## Quick start

```bash
# 1. Create an isolated environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate the synthetic dataset
python data/generate_data.py

# 4. Launch the dashboard
streamlit run app.py
```

Then open the URL Streamlit prints (default http://localhost:8501).

---

## Project structure

```
cost-driver-dashboard/
├── app.py                     # Streamlit UI (charts, filters, KPIs)
├── data/
│   ├── generate_data.py       # Synthetic data generator (the analytical model)
│   └── cost_facts.csv         # Generated fact table (created on step 3)
├── src/
│   └── analytics.py           # UI-free analytics engine (testable core logic)
├── tests/
│   └── test_analytics.py      # Reconciliation & correctness tests
├── powerbi/                   # Enterprise Power BI package
│   ├── export_star_schema.py  # Builds the star-schema model CSVs
│   ├── model/                 # Import-ready dimension & fact tables
│   ├── measures.dax           # Ready-to-paste DAX measures
│   ├── theme.json             # Corporate colour theme
│   └── POWERBI_GUIDE.md       # Step-by-step build guide
├── requirements.txt
└── README.md
```

---

## Power BI version (enterprise)

Prefer an enterprise Power BI report? The [`powerbi/`](powerbi/POWERBI_GUIDE.md)
folder ships a full **star-schema model**, **DAX measures**, and a corporate **theme**
so you can build a polished, refreshable Power BI report in ~15 minutes:

```bash
python powerbi/export_star_schema.py   # generates powerbi/model/*.csv
```

Then follow [`powerbi/POWERBI_GUIDE.md`](powerbi/POWERBI_GUIDE.md) to import the model,
paste the measures, apply the theme, and lay out the report (KPIs → waterfall →
vendor opportunity table). Power BI Desktop is Windows-only, which is why the package
ships as import-ready assets rather than a binary `.pbix`.

---

## The data model

Each row of `data/cost_facts.csv` is one **SKU in one fiscal quarter**. Landed unit
cost is stored as an exactly additive decomposition:

```
unit_cost = material_cost   # commodity index driven (local currency)
          + freight_cost    # freight index driven
          + fx_impact       # isolated currency movement vs. USD
          + vendor_cost     # vendor pricing / negotiation behavior
          + tariff_cost     # duty / tariff
```

`extended_cost = unit_cost × units`.

Vendors are modeled with distinct pricing behaviors — *aggressive* (raises faster than
commodities, resists drops), *sticky* (slow to pass savings back), and *fair* (tracks
commodities) — which is what surfaces the **vendor-driven / negotiation opportunity**
metric.

### Using real data

Replace `data/cost_facts.csv` with your own file using the same columns:

```
period, sku, product_name, category, commodity, vendor, currency, units,
material_cost, freight_cost, fx_impact, vendor_cost, tariff_cost,
unit_cost, extended_cost
```

`period` is `YYYY-Qn` (e.g. `2025-Q3`).

---

## Running the tests

```bash
python tests/test_analytics.py
```

The suite verifies the additive decomposition, waterfall reconciliation, KPI
consistency, and filtering behavior.

---

## Presenting to leadership

Suggested 3-minute narrative:

1. **Start with the KPI row** — total cost change and the addressable, vendor-driven slice.
2. **Walk the waterfall** — "Cost rose $X; here's the split: commodities did this,
   freight this, FX this, and *this* portion is vendor pricing we can negotiate."
3. **Land on the vendor table** — a prioritized, dollar-sized negotiation target list.

This connects market intelligence to a concrete, fact-based savings pipeline —
exactly the value a Sourcing Advisory Analyst delivers.

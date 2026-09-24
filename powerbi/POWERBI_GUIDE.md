# Power BI Report — Build Guide

This folder turns the Cost Driver Dashboard into an **enterprise Power BI report**.
Power BI Desktop is Windows-only, so rather than a binary `.pbix` you get a clean,
import-ready **star schema**, ready-to-paste **DAX measures**, and a corporate
**theme** — the same assets a BI developer would hand off in a real engagement.

> Total build time in Power BI Desktop: ~15–20 minutes.

---

## 0. What's in this folder

| File | Purpose |
|------|---------|
| `export_star_schema.py` | Generates the model CSVs from the cost data |
| `model/*.csv` | The star-schema tables to import |
| `measures.dax` | All DAX measures, ready to paste |
| `theme.json` | Enterprise colour theme (corporate blue, red=cost up, green=cost down) |
| `POWERBI_GUIDE.md` | This guide |

Regenerate the model any time the data changes:

```bash
python powerbi/export_star_schema.py
```

---

## 1. The data model (star schema)

```
                         ┌───────────────┐
                         │  DimPeriod    │
                         │  period (PK)  │
                         │  date, year…  │
                         └───────┬───────┘
                                 │ 1
                                 │
        ┌───────────────┐        │ *      ┌───────────────┐
        │  DimProduct   │1     * │      * │  DimVendor    │
        │  sku (PK)     ├────────┼────────┤  vendor (PK)  │
        └───────────────┘        │        └───────────────┘
                                 │
                         ┌───────┴────────┐
                         │ FactCostDriver │   grain: period × SKU × driver
                         │  cost_ext      │
                         └───────┬────────┘
                                 │ *
                                 │ 1
                         ┌───────┴───────┐
                         │  DimDriver    │
                         │  driver (PK)  │
                         └───────────────┘

   Disconnected slicers:  DimStartPeriod   DimEndPeriod   (no relationships)
```

**Why the fact is unpivoted:** each cost driver (commodity, freight, FX, vendor,
tariff) is its own row, so a single measure (`SUM(cost_ext)`) powers every visual and
the Waterfall can pivot on `DimDriver[driver]`. This is the idiomatic, fast Power BI
pattern.

---

## 2. Import the data

1. Open **Power BI Desktop** → **Home → Get Data → Text/CSV** (or **Folder** to grab
   all seven at once from `powerbi/model/`).
2. Import all seven CSVs:
   `DimPeriod`, `DimProduct`, `DimVendor`, `DimDriver`, `FactCostDriver`,
   `DimStartPeriod`, `DimEndPeriod`.
3. In **Model view**, create these relationships (single-direction, 1 → many):

   | From (1) | To (many) |
   |----------|-----------|
   | `DimPeriod[period]` | `FactCostDriver[period]` |
   | `DimProduct[sku]` | `FactCostDriver[sku]` |
   | `DimVendor[vendor]` | `FactCostDriver[vendor]` |
   | `DimDriver[driver]` | `FactCostDriver[driver]` |

   Leave **`DimStartPeriod`** and **`DimEndPeriod`** with **no relationships** — they
   are intentionally disconnected slicers.
4. Mark **`DimPeriod[date]`** as a date column (Column tools → Data type = Date) and
   sort **`DimPeriod[period]`** by `period_order`. Sort **`DimDriver[driver]`** by
   `sort_order`.

---

## 3. Add the measures

Create a measures home table (recommended): **Home → Enter Data**, name it
`_Measures`, add one dummy column, load, then hide the column.

Open `measures.dax`, and for each measure block: **Modeling → New Measure**, paste,
press Enter. Set number formatting on `Total Cost`, `Cost at Start/End`,
`Cost Change` → Currency; `Cost Change %` and `Vendor-Driven % of Total Change` →
Percentage.

---

## 4. Apply the enterprise theme

**View → Themes → Browse for themes →** select `powerbi/theme.json`.

This sets the corporate palette and, importantly, makes the **Waterfall** show
**cost increases in red and decreases in green** automatically.

---

## 5. Build the report page

Suggested single-page layout (top to bottom):

**A. Slicer bar (top)**
- Slicer: `DimStartPeriod[start_period]` → label "From"
- Slicer: `DimEndPeriod[end_period]` → label "To"
- Slicers: `DimProduct[category]`, `DimVendor[vendor]`, `DimProduct[commodity]`

**B. KPI cards (row of four)**
- Card → `[Cost at Start]`  (title "Total Cost — Start")
- Card → `[Cost at End]`    (title "Total Cost — End")
- Card → `[Cost Change]`    (title "Cost Change"; conditional font colour = `[Cost Change Colour]`)
- Card → `[Vendor-Driven Change]` (title "Addressable — Vendor-Driven")

**C. Flagship Waterfall**
- Visual: **Waterfall chart**
- Category: `DimDriver[driver]`
- Y: `[Driver Delta]`
- This reads: start total → each driver's contribution → end total.

**D. Trend + category (two visuals side by side)**
- **Stacked area chart** — Axis `DimPeriod[date]`, Legend `DimDriver[driver]`, Values `[Total Cost]`.
- **Stacked bar chart** — Axis `DimProduct[category]`, Legend `DimDriver[driver]`, Values `[Driver Delta]`.

**E. Vendor opportunity table**
- **Table/Matrix** — Rows `DimVendor[vendor]`; Values `[Cost at Start]`,
  `[Cost at End]`, `[Cost Change]`, `[Cost Change %]`, `[Vendor-Driven Change]`.
- Sort by `[Cost Change]` desc; add data bars to `[Cost Change]` via conditional formatting.

---

## 6. Presenting to leadership (3-minute script)

1. **KPIs** — "Total cost moved `[Cost Change]`; of that, `[Vendor-Driven Change]` is
   addressable through negotiation."
2. **Waterfall** — walk left to right: "Commodities drove this, freight this, FX this,
   and *this* red bar is vendor pricing beyond pass-through."
3. **Vendor table** — "Here's the prioritised, dollar-sized negotiation target list."

That chain — market drivers → isolated vendor opportunity → prioritised target list —
is exactly the fact-based value a Sourcing Advisory Analyst delivers.

---

## 7. Publishing (optional)

**Home → Publish** to a Power BI Service workspace to share a live, refreshable
dashboard. Point the CSV source at a shared/SharePoint folder (or a database) to enable
**Scheduled Refresh** so the report stays current automatically.

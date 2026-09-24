# Savings & Negotiation Tracker

A **governed repository** of sourcing savings initiatives. It tracks every
negotiation from *identification* through *realized savings*, measures the
**realization rate** (did the promised savings actually land?), and keeps an
**append-only audit trail** of every change — the data-governance backbone a
Sourcing Advisory Analyst is expected to own.

Built with **Streamlit + SQLite** with full **CRUD**, so you can add, edit, and
close initiatives through the UI while every change is logged.

> Runs on realistic **synthetic data** seeded into SQLite. Everything you enter
> persists in the local database.

---

## What it shows

| Area | Business question it answers |
|------|------------------------------|
| **KPI row** | How big is the savings pipeline, how much is realized, and what's the realization rate? |
| **Pipeline by Status** | Where do initiatives sit in the funnel (Identified → Realized)? |
| **Realized Savings Over Time** | When did savings actually land? |
| **Projected vs Realized by Category** | Which categories deliver vs. under-deliver? |
| **Realization Rate by Owner** | Who is closing the savings they commit to? |
| **At-Risk Watch-List** | Which initiatives are overdue and need attention? |
| **Audit Log** | Full change history for governance & auditability. |

The **realization rate** metric is the headline: it exposes the gap between
*promised* and *delivered* savings — exactly what leadership wants visibility into.

---

## Quick start

```bash
# 1. Create an isolated environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Seed the SQLite database with sample initiatives
python data/seed_data.py

# 4. Launch the app
streamlit run app.py
```

Open the URL Streamlit prints (default http://localhost:8501). If the database
doesn't exist yet, the app initialises and seeds it automatically on first run.

---

## Project structure

```
savings-tracker/
├── app.py                     # Streamlit UI: Dashboard, Manage (CRUD), Audit Log
├── data/
│   ├── schema.sql             # SQLite DDL: tables, view, status reference
│   ├── seed_data.py           # Generates a realistic portfolio of initiatives
│   └── savings.db             # SQLite database (created on seed; git-ignored)
├── src/
│   ├── db.py                  # Connection handling + schema init
│   ├── constants.py           # Status workflow, savings types, vocab
│   ├── repository.py          # CRUD data-access layer with audit logging
│   └── analytics.py           # KPIs, realization rate, pipeline analytics
├── tests/
│   └── test_repository.py     # CRUD, audit, validation & analytics tests
├── requirements.txt
└── README.md
```

---

## Data model

**`initiatives`** — one row per negotiation / savings initiative:

| Field | Meaning |
|-------|---------|
| `baseline_unit_cost`, `negotiated_unit_cost`, `annual_volume` | inputs to projected savings |
| `projected_savings` *(view)* | `(baseline − negotiated) × volume` |
| `realized_savings` | actual savings booked so far |
| `realization_rate` *(view)* | `realized ÷ projected` |
| `status` | Identified → In Negotiation → Agreed → Implemented → Realized / Cancelled |
| `owner`, `category`, `vendor`, `savings_type`, `confidence` | dimensions for analysis |
| `start_date`, `target_close_date`, `realized_date` | timeline & at-risk detection |

**`audit_log`** — append-only; one row per changed field on every update
(`old_value` → `new_value`, who, when). Foreign-keyed to `initiatives` with
`ON DELETE CASCADE`.

**`v_initiative_metrics`** — a SQL view that computes `projected_savings` and
`realization_rate` so every read is consistent.

---

## Governance features

- **Audit trail**: every create/update writes to `audit_log`; the UI's *Audit Log*
  page renders and exports the full history.
- **Status workflow**: a `status_ref` table documents the allowed states and which
  are terminal, enforced by a foreign key.
- **Validation**: the repository rejects missing required fields, negative numbers,
  and flags negotiated > baseline (negative savings) before writing.
- **Constraints**: `CHECK` constraints on the table guard data integrity at the DB level.

---

## Running the tests

```bash
python tests/test_repository.py
```

Covers projected-savings/realization-rate calculation, audit logging on update,
no-op detection, validation, cascade delete, and the analytics KPIs — using a
throwaway temp database so your real data is untouched.

---

## Presenting to leadership (3-minute script)

1. **KPI row** — "We have `$X` of projected savings; `$Y` realized — a `Z%`
   realization rate."
2. **Pipeline funnel + at-risk list** — "Here's what's in-flight, and these overdue
   initiatives need intervention."
3. **Realization by owner / category** — "Here's who and what reliably converts
   commitments into booked savings."

This turns scattered negotiation notes into a **governed, measurable savings
program** — a direct demonstration of results orientation and continuous improvement.

---

## Pairs with the Cost Driver Dashboard

This tracker answers *"are we capturing the savings?"*; the companion
**Cost Driver Dashboard** answers *"why is cost moving?"*. Together they form a
complete sourcing-analytics portfolio.

# 🚀 Running Both Apps Together

This unified project combines two complementary sourcing analytics tools:
- **Cost Driver Dashboard** — Explains *why* cost is moving
- **Savings Tracker** — Tracks *if* savings are being realized

## Quick Start (One Command)

```bash
./run_both.sh
```

Both apps will launch simultaneously:
- **Cost Driver Dashboard**: http://localhost:8501
- **Savings Tracker**: http://localhost:8502

## Project Structure

```
cost-driver-dashboard/
├── app.py                          # Cost Driver Dashboard (port 8501)
├── data/
│   ├── generate_data.py            # Generates synthetic cost facts
│   └── cost_facts.csv              # Generated dataset
├── src/analytics.py                # Cost analytics engine
├── tests/
├── requirements.txt
├── .venv/                          # Virtual environment
│
├── modules/
│   └── savings-tracker/            # Merged Savings Tracker module
│       ├── app.py                  # Savings Tracker UI (port 8502)
│       ├── data/
│       │   ├── schema.sql          # SQLite DDL
│       │   ├── seed_data.py        # Database seeding
│       │   └── savings.db          # SQLite database
│       ├── src/
│       │   ├── db.py
│       │   ├── repository.py       # CRUD operations
│       │   └── analytics.py        # Savings analytics
│       ├── tests/
│       ├── requirements.txt
│       └── .venv/                  # Separate virtual environment
│
├── run_both.sh                     # Bash launcher
├── run_both.py                     # Python launcher (alternative)
└── RUN_BOTH.md                     # This file
```

---

## 📊 Typical Workflow

### Phase 1: Cost Analysis
**Cost Driver Dashboard** (http://localhost:8501)
1. Navigate to the dashboard
2. Review KPI cards → see total cost change
3. Examine the **Cost Change Waterfall** → identify drivers
4. Check **Vendor Opportunity Table** → find negotiation targets
5. **Key insight**: "Vendor X raised prices $500K beyond commodity movements"

### Phase 2: Savings Capture
**Savings Tracker** (http://localhost:8502)
1. Go to **Manage Initiatives** tab
2. Click **➕ Add New**
3. Record the negotiation details:
   - Initiative name: "Negotiate Vendor X pricing"
   - Baseline unit cost: (from Cost Driver Dashboard)
   - Negotiated unit cost: (your target)
   - Annual volume: (from Cost Driver Dashboard)
   - Status: "In Negotiation"
4. Submit → projected savings auto-calculated

### Phase 3: Realization Tracking
1. As you close negotiations → update Status to "Agreed" → "Implemented"
2. When savings land in cost data → record "Realized" status
3. **Realization Rate** shows: "We promised $500K, realized $420K = 84%"
4. **At-Risk Watch-List** flags overdue initiatives

---

## Manual Setup (If Needed)

### Install Cost Driver Dashboard
```bash
cd cost-driver-dashboard
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python data/generate_data.py           # Generate demo data
streamlit run app.py                   # Launch on port 8501
```

### Install Savings Tracker
```bash
cd cost-driver-dashboard/modules/savings-tracker
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python data/seed_data.py               # Seed database
streamlit run app.py                   # Launch on port 8502
```

---

## 📱 Using Both Apps

### In Cost Driver Dashboard (Port 8501)
- **Sidebar filters**: Category, Vendor, Commodity
- **Waterfall chart**: See exact cost driver breakdown
- **Vendor table**: Ranked by cost increase
- **Download detail**: Export SKU-level data for negotiation prep

### In Savings Tracker (Port 8502)
- **Dashboard tab**: KPIs, pipeline funnel, realization rate
- **Manage Initiatives tab**: Add/edit/delete initiatives with full audit trail
- **Audit Log tab**: Complete change history for governance
- **Filters**: Status, Category, Vendor, Owner

### Key Metrics Connection
| Question | Cost Driver Dashboard | Savings Tracker |
|----------|----------------------|-----------------|
| "Why is cost moving?" | ✅ Cost change decomposition | — |
| "How much can we save?" | ✅ Vendor-driven change | — |
| "What did we commit to?" | — | ✅ Projected savings |
| "What did we actually save?" | — | ✅ Realized savings |
| "Are we hitting targets?" | — | ✅ Realization rate % |

---

## 🔄 Data Flow

```
Real Cost Data
    ↓
Cost Driver Dashboard
    ├─→ Identifies cost drivers
    └─→ Highlights vendor negotiation opportunities
         ↓
    Feeds insight to...
         ↓
Savings Tracker
    ├─→ Records negotiation initiatives
    ├─→ Tracks implementation progress
    └─→ Measures realization rate
         ↓
    Outcome: "Did we capture the savings?"
```

---

## 🧪 Running Tests

### Cost Driver Dashboard
```bash
cd cost-driver-dashboard
source .venv/bin/activate
python tests/test_analytics.py
```

### Savings Tracker
```bash
cd cost-driver-dashboard/modules/savings-tracker
source .venv/bin/activate
python tests/test_repository.py
```

---

## 🔧 Troubleshooting

### Port already in use
If port 8501 or 8502 is already taken:
```bash
# Kill the process using the port
lsof -i :8501  # or :8502
kill -9 <PID>

# Or manually adjust ports in run_both.sh
```

### Virtual environment issues
```bash
# Recreate environments from scratch
rm -rf cost-driver-dashboard/.venv
rm -rf cost-driver-dashboard/modules/savings-tracker/.venv
./run_both.sh
```

### Database reset
```bash
# Reset Savings Tracker database
rm cost-driver-dashboard/modules/savings-tracker/data/savings.db
cd cost-driver-dashboard/modules/savings-tracker
python data/seed_data.py
```

---

## 📚 Documentation

- **Cost Driver Dashboard**: See `cost-driver-dashboard/README.md`
- **Savings Tracker**: See `cost-driver-dashboard/modules/savings-tracker/README.md`
- **Power BI Option**: See `cost-driver-dashboard/powerbi/POWERBI_GUIDE.md`

---

## 🎯 Best Practices

1. **Start with Cost Driver Dashboard** to identify opportunities
2. **Record in Savings Tracker** within 48 hours of initiating negotiation
3. **Update status regularly** to keep the pipeline current
4. **Export data** for stakeholder presentations
5. **Monitor realization rate** monthly to track execution discipline

---

## 🤝 Tips for Presenting to Leadership

### 5-Minute Narrative
1. **(1 min)** Show Cost Driver Dashboard waterfall → "Here's why cost moved"
2. **(1 min)** Click vendor table → "Here are the negotiation targets"
3. **(1 min)** Switch to Savings Tracker → "Here's what we've committed to capture"
4. **(1 min)** Show realization rate → "And here's our track record of delivery"
5. **(1 min)** At-risk list → "These initiatives need attention this week"

**Narrative**: "We use data to identify savings opportunities and track them through realization. This quarter we identified $X, committed to $Y, and delivered $Z — a [realization_rate]% conversion rate."

---

Enjoy your unified sourcing analytics platform! 🚀

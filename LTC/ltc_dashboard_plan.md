# LTC Cost & Mortality Risk Dashboard
### A Weekend Actuarial Project | Good Samaritan Society Positioning

---

## 1. Project Overview

**What it is:** A Python-based actuarial model that estimates long-term care (LTC) cost projections by age cohort using public CMS, CDC, and SOA data, surfaced via a clean Streamlit dashboard with interactive sensitivity controls.

**Real-world application:** Good Samaritan Society and similar senior living operators need to forecast future care costs per resident, model occupancy break-even thresholds, and stress-test financial assumptions under different inflation/discount scenarios. This project mirrors that exact workflow using publicly available data — the same sources actuarial analysts actually use.

**Deliverable:** A deployed Streamlit app at `surehsan.com` with documented code and a README that frames it in actuarial language.

---

## 2. Real-Life Senior Home Application

| Model Output | How a Senior Home Uses It |
|---|---|
| Present value of future care costs by cohort | Pricing assisted living contracts, insurance reserves |
| Survival probability curves | Estimating average length of stay per admission type |
| Sensitivity to inflation rate | Budgeting for labor/supply cost increases (CPI, wage inflation) |
| Sensitivity to discount rate | Capital planning, bond issuance decisions |
| Break-even occupancy % | Minimum census needed to cover fixed overhead |

**Concrete example:** If Good Samaritan admits a 78-year-old into memory care at $8,500/month, what is the expected present value of total care costs over their projected stay, discounted at 4.5%? This model answers that.

---

## 3. Tech Stack

| Layer | Tool | Reason |
|---|---|---|
| Data processing | `pandas`, `numpy` | Standard for tabular actuarial data; readable by any analyst |
| Actuarial math | `numpy` (vectorized) | Survival functions, PV calculations — no heavy dependencies |
| **Data warehouse** | **SQLite + DuckDB** | **Stores cleaned CMS/SOA/CDC data in queryable tables; all model inputs pulled via SQL** |
| Visualization | `matplotlib`, `plotly` | Plotly preferred for Streamlit interactivity |
| **BI reporting** | **Tableau Public / Power BI Desktop** | **Executive-facing dashboard layer on top of the SQLite DB; mirrors real actuarial team workflows** |
| Dashboard | `Streamlit` | Fast to deploy, Python-native, professional output |
| Data storage | SQLite `.db` file | Single-file DB; CMS/CDC CSVs loaded once, queried repeatedly |
| Environment | `venv` + `requirements.txt` | Clean, portable, interview-ready |
| Deployment | Streamlit Community Cloud | Free, connects to GitHub, live at custom domain via surehsan.com |
| Version control | `git` + GitHub | Required for deployment; documents your workflow |

---

## 4. Data Sources

### 4.1 CDC WONDER — Mortality Rates
- **URL:** https://wonder.cdc.gov/
- **What to pull:** Underlying cause of death, grouped by age band (65–69, 70–74, 75–79, 80–84, 85+) and sex
- **Format:** Downloadable `.txt`/`.csv` via query interface
- **Actuarial use:** Derives `qx` — probability of death at age x — the foundation of any life table

### 4.2 CMS MDS / Nursing Home Data
- **URL:** https://data.cms.gov/provider-data/topics/nursing-homes
- **What to pull:** Nursing Home Compare datasets — staffing, quality measures, resident census counts
- **Format:** Direct `.csv` download
- **Actuarial use:** LTC admission rates by facility type; average length of stay proxies; quality-adjusted care level classification

### 4.3 SOA Mortality Tables
- **URL:** https://mort.soa.org/
- **What to pull:** 2012 IAM (Individual Annuitant Mortality) table or RP-2014 table — industry standard for LTC modeling
- **Format:** Excel download, convert to `.csv`
- **Actuarial use:** Industry-validated `qx`/`lx` columns for survival probability calculations; more reliable than CDC for actuarial pricing

---

## 5. Project Structure

```
ltc-dashboard/
│
├── data/
│   ├── raw/
│   │   ├── cdc_mortality.csv
│   │   ├── cms_nursing_home.csv
│   │   └── soa_iam_2012.csv
│   └── processed/
│       ├── survival_table.csv
│       └── cost_projections.csv
│
├── db/
│   ├── schema.sql             # Table definitions
│   ├── load.py                # CSV → SQLite loader
│   └── ltc.db                 # SQLite database (gitignored, rebuilt from raw)
│
├── sql/
│   ├── cohort_mortality.sql   # qx by age band
│   ├── cost_projections.sql   # PV outputs by cohort
│   └── breakeven_summary.sql  # Facility-level break-even view
│
├── tableau/
│   └── ltc_dashboard.twbx     # Packaged Tableau workbook (connects to ltc.db)
│
├── src/
│   ├── ingest.py          # Load + clean raw data → SQLite
│   ├── life_table.py      # Build lx, qx, ex columns
│   ├── cost_model.py      # PV of future care costs
│   ├── breakeven.py       # Occupancy break-even model
│   └── utils.py           # Shared helpers
│
├── app.py                 # Streamlit dashboard entry point
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 6. Pipeline — Step by Step

### Step 1: Ingest & Clean (`src/ingest.py`)

```python
import pandas as pd

def load_soa_table(path: str) -> pd.DataFrame:
    """Load SOA IAM mortality table. Expects columns: age, qx, lx."""
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    df = df[df['age'].between(65, 100)]
    return df.reset_index(drop=True)

def load_cdc_mortality(path: str) -> pd.DataFrame:
    """Load CDC WONDER export. Derive qx from deaths/population."""
    df = pd.read_csv(path, sep='\t', skipfooter=15, engine='python')
    df = df.dropna(subset=['Deaths', 'Population'])
    df['qx'] = df['Deaths'] / df['Population']
    return df[['Age Group', 'qx']]
```

**Why:** Keeping ingestion isolated means you can swap data sources without touching the model logic.

---

### Step 1b: Load to SQLite (`db/load.py` + `db/schema.sql`)

**Schema:**

```sql
-- db/schema.sql

CREATE TABLE IF NOT EXISTS mortality_rates (
    age         INTEGER NOT NULL,
    sex         TEXT,
    qx          REAL NOT NULL,         -- probability of death at age x
    source      TEXT DEFAULT 'SOA'     -- 'SOA' | 'CDC'
);

CREATE TABLE IF NOT EXISTS cost_projections (
    age_entry       INTEGER NOT NULL,
    care_level      TEXT NOT NULL,
    year_t          INTEGER NOT NULL,  -- years from entry
    survival_prob   REAL NOT NULL,
    expected_cost   REAL NOT NULL,     -- inflation-adjusted, survival-weighted
    pv_cost         REAL NOT NULL      -- discounted present value
);

CREATE TABLE IF NOT EXISTS breakeven_summary (
    facility_id         TEXT,
    total_beds          INTEGER,
    fixed_costs         REAL,
    revenue_per_bed     REAL,
    variable_per_bed    REAL,
    breakeven_pct       REAL,
    contribution_margin REAL
);
```

**Loader:**

```python
# db/load.py
import sqlite3
import pandas as pd

def load_csv_to_db(csv_path: str, table: str, db_path: str = "db/ltc.db"):
    conn = sqlite3.connect(db_path)
    df = pd.read_csv(csv_path)
    df.to_sql(table, conn, if_exists='replace', index=False)
    conn.close()
    print(f"Loaded {len(df)} rows → {table}")

if __name__ == "__main__":
    load_csv_to_db("data/processed/survival_table.csv", "mortality_rates")
    load_csv_to_db("data/processed/cost_projections.csv", "cost_projections")
```

**Why:** SQLite gives you a real queryable database from a single file — no server setup. DuckDB is a drop-in alternative if you want faster analytical queries on larger CMS datasets (`pip install duckdb`). Both connect directly to Tableau and Power BI via ODBC.

---

### Step 1c: Analytical SQL Queries (`sql/`)

```sql
-- sql/cohort_mortality.sql
-- Average qx and life expectancy by 5-year age band
SELECT
    (age / 5) * 5                    AS age_band_start,
    (age / 5) * 5 + 4                AS age_band_end,
    ROUND(AVG(qx), 5)                AS avg_qx,
    COUNT(*)                         AS ages_in_band
FROM mortality_rates
WHERE age BETWEEN 65 AND 100
GROUP BY age_band_start
ORDER BY age_band_start;
```

```sql
-- sql/cost_projections.sql
-- Total PV of care costs by entry age and care level
SELECT
    age_entry,
    care_level,
    ROUND(SUM(pv_cost), 2)           AS total_pv_cost,
    ROUND(AVG(survival_prob), 4)     AS avg_survival_prob,
    COUNT(*)                         AS projection_years
FROM cost_projections
GROUP BY age_entry, care_level
ORDER BY age_entry, care_level;
```

```sql
-- sql/breakeven_summary.sql
-- Facilities below break-even threshold (census risk flag)
SELECT
    facility_id,
    total_beds,
    ROUND(breakeven_pct, 1)          AS breakeven_pct,
    ROUND(contribution_margin, 2)    AS contribution_margin,
    CASE
        WHEN breakeven_pct > 90 THEN 'HIGH RISK'
        WHEN breakeven_pct BETWEEN 80 AND 90 THEN 'WATCH'
        ELSE 'STABLE'
    END                              AS census_risk_flag
FROM breakeven_summary
ORDER BY breakeven_pct DESC;
```

**Why:** These queries are what a Good Sam finance analyst would actually run in a reporting tool. Writing them yourself proves SQL fluency beyond "I know SELECT."

---

### Step 2: Build Survival Table (`src/life_table.py`)

```python
import numpy as np
import pandas as pd

def build_life_table(qx_series: pd.Series, start_age: int = 65, radix: int = 100_000) -> pd.DataFrame:
    """
    Builds standard actuarial life table.
    qx  = probability of death in year x
    lx  = number alive at age x (from radix)
    dx  = expected deaths in year x
    ex  = curtate life expectancy at age x
    """
    ages = range(start_age, start_age + len(qx_series))
    lx = [radix]
    dx = []

    for q in qx_series:
        d = lx[-1] * q
        dx.append(d)
        lx.append(lx[-1] - d)

    lx = lx[:-1]
    px = 1 - qx_series.values  # probability of survival

    # Curtate life expectancy
    ex = [sum(np.prod(px[i:i+k]) for k in range(1, len(px)-i)) for i in range(len(px))]

    return pd.DataFrame({'age': ages, 'qx': qx_series.values, 'lx': lx, 'dx': dx, 'ex': ex})
```

**Why:** `lx` and `qx` are the actuarial primitives everything else is built on. This is the exact structure in the SOA tables.

---

### Step 3: Present Value of Future Care Costs (`src/cost_model.py`)

```python
import numpy as np

CARE_COSTS = {
    'independent_living': 3_500,
    'assisted_living': 6_200,
    'memory_care': 8_500,
    'skilled_nursing': 11_000,
}

def pv_future_costs(
    age: int,
    care_level: str,
    monthly_cost: float,
    discount_rate: float,
    inflation_rate: float,
    survival_probs: list[float]
) -> float:
    """
    Calculates present value of expected future LTC costs from entry age.

    PV = Σ [ (monthly_cost * 12 * (1+i)^t * p_t) / (1+d)^t ]
    where:
        i = annual inflation rate
        d = annual discount rate
        p_t = probability of surviving to year t from entry age
    """
    pv = 0.0
    annual_cost = monthly_cost * 12

    for t, p_survive in enumerate(survival_probs):
        inflated_cost = annual_cost * ((1 + inflation_rate) ** t)
        discounted = inflated_cost * p_survive / ((1 + discount_rate) ** t)
        pv += discounted

    return round(pv, 2)
```

**Why:** This is the core actuarial formula. Interviewers at Good Sam will recognize it immediately. The separation of `inflation_rate` and `discount_rate` is deliberate — they move independently and drive the sensitivity analysis.

---

### Step 4: Break-Even Occupancy Model (`src/breakeven.py`)

```python
def breakeven_occupancy(
    fixed_costs_monthly: float,
    revenue_per_resident: float,
    variable_cost_per_resident: float,
    total_beds: int
) -> dict:
    """
    Calculates minimum occupancy % to cover fixed costs.

    Contribution margin = revenue_per_resident - variable_cost_per_resident
    Break-even residents = fixed_costs / contribution_margin
    Break-even % = break_even_residents / total_beds
    """
    contribution_margin = revenue_per_resident - variable_cost_per_resident
    if contribution_margin <= 0:
        raise ValueError("Revenue must exceed variable cost per resident.")

    breakeven_residents = fixed_costs_monthly / contribution_margin
    breakeven_pct = (breakeven_residents / total_beds) * 100

    return {
        'breakeven_residents': round(breakeven_residents, 1),
        'breakeven_pct': round(breakeven_pct, 1),
        'contribution_margin': round(contribution_margin, 2),
    }
```

**Real-world tie-in:** Good Samaritan Society operates 150+ facilities. Each facility has fixed overhead (salaries, utilities, mortgage/lease). The finance team tracks census daily. At ~85–88% occupancy, most LTC facilities break even — this model surfaces exactly that threshold dynamically.

---

### Step 5: Streamlit Dashboard (`app.py`)

```python
import streamlit as st
import plotly.express as px
import pandas as pd
from src.ingest import load_soa_table
from src.life_table import build_life_table
from src.cost_model import pv_future_costs, CARE_COSTS
from src.breakeven import breakeven_occupancy

st.set_page_config(page_title="LTC Cost & Mortality Dashboard", layout="wide")
st.title("Long-Term Care Cost & Mortality Risk Dashboard")
st.caption("Actuarial modeling for senior living facilities | Data: SOA, CMS, CDC")

# --- Sidebar controls ---
st.sidebar.header("Model Parameters")
entry_age = st.sidebar.slider("Resident Entry Age", 65, 90, 78)
care_level = st.sidebar.selectbox("Care Level", list(CARE_COSTS.keys()))
monthly_cost = st.sidebar.number_input("Monthly Cost ($)", value=CARE_COSTS[care_level])
discount_rate = st.sidebar.slider("Discount Rate (%)", 1.0, 10.0, 4.5) / 100
inflation_rate = st.sidebar.slider("Inflation Rate (%)", 0.0, 8.0, 3.5) / 100

# --- Life table ---
df_soa = load_soa_table("data/processed/survival_table.csv")
df_lt = build_life_table(df_soa[df_soa['age'] >= entry_age]['qx'].reset_index(drop=True))

# --- PV calculation ---
survival_probs = (df_lt['lx'] / df_lt['lx'].iloc[0]).tolist()
pv = pv_future_costs(entry_age, care_level, monthly_cost, discount_rate, inflation_rate, survival_probs)

# --- Main metrics ---
col1, col2, col3 = st.columns(3)
col1.metric("PV of Future Care Costs", f"${pv:,.0f}")
col2.metric("Life Expectancy from Entry", f"{df_lt['ex'].iloc[0]:.1f} yrs")
col3.metric("Entry Age", entry_age)

# --- Survival curve ---
st.subheader("Survival Probability Curve")
fig = px.line(df_lt, x='age', y='lx', title=f"Survivors from Age {entry_age} (Radix = 100,000)")
st.plotly_chart(fig, use_container_width=True)

# --- Cost projection curve ---
st.subheader("Annual Care Cost Projection (Inflation-Adjusted)")
years = list(range(len(survival_probs)))
costs = [monthly_cost * 12 * ((1 + inflation_rate) ** t) * survival_probs[t] for t in years]
fig2 = px.area(x=[entry_age + t for t in years], y=costs,
               labels={'x': 'Age', 'y': 'Expected Annual Cost ($)'})
st.plotly_chart(fig2, use_container_width=True)

# --- Break-even section ---
st.subheader("Facility Break-Even Occupancy")
with st.expander("Configure Facility Parameters"):
    fixed_costs = st.number_input("Fixed Monthly Costs ($)", value=850_000)
    revenue_per = st.number_input("Revenue per Resident/Month ($)", value=monthly_cost)
    variable_per = st.number_input("Variable Cost per Resident/Month ($)", value=2_800)
    total_beds = st.number_input("Total Facility Beds", value=120)

be = breakeven_occupancy(fixed_costs, revenue_per, variable_per, total_beds)
st.metric("Break-Even Occupancy", f"{be['breakeven_pct']}%")
st.metric("Break-Even Resident Count", f"{be['breakeven_residents']} / {total_beds} beds")
```

---

---

## 6b. Tableau / Power BI Layer

This layer sits **on top of the SQLite database** and produces an executive-facing report — the kind a Good Sam VP of Finance or Regional Director would actually open, not a developer.

### Why Both?
- **Tableau Public** — free, shareable via public URL, embeddable in `surehsan.com`
- **Power BI Desktop** — free download, `.pbix` file in repo signals Microsoft stack fluency (common in health systems)

Build one, mention both in the README.

---

### Tableau Setup

1. Download **Tableau Public** (free): https://public.tableau.com/
2. Connect to data: `Connect → SQLite` (requires SQLite ODBC driver) **or** connect directly to `cost_projections.csv` as a simpler alternative for the weekend
3. Build these 3 sheets:

| Sheet | Chart Type | Fields |
|---|---|---|
| **Survival Curves** | Line chart | `age` (x), `lx` (y), `care_level` (color) |
| **PV Cost by Cohort** | Bar chart | `age_entry` (x), `total_pv_cost` (y), `care_level` (color) |
| **Break-Even Risk** | Highlight table | `facility_id` (row), `breakeven_pct` (value), `census_risk_flag` (color) |

4. Assemble into a **Dashboard** with title: `LTC Cost & Mortality Risk — Actuarial Summary`
5. Publish to Tableau Public → copy embed URL → add to `surehsan.com`

---

### Power BI Setup

1. Download **Power BI Desktop** (free): https://powerbi.microsoft.com/desktop
2. `Get Data → Text/CSV` → load `cost_projections.csv` and `breakeven_summary.csv`
3. In Power Query, add a calculated column for risk flag:

```
census_risk_flag = 
IF([breakeven_pct] > 90, "HIGH RISK",
IF([breakeven_pct] >= 80, "WATCH", "STABLE"))
```

4. Build a single-page report with:
   - **Card visuals:** Avg PV cost, Avg break-even %, Total cohorts modeled
   - **Line chart:** Survival probability by age and care level
   - **Matrix:** Entry age × Care level → Total PV cost (heatmap formatting)
   - **Slicer:** Discount rate band, Inflation rate band

5. Save as `ltc_dashboard.pbix` → commit to `tableau/` folder in repo

---

### Connecting Power BI to SQLite (Optional, Stronger Signal)

```
Get Data → ODBC → DSN: SQLite3 Datasource
Connection string: Driver={SQLite3 ODBC Driver};Database=db/ltc.db
```

Then write DirectQuery against your SQL views — this is what enterprise analysts do and will stand out in an interview.

```bash
# 1. Push to GitHub
git init
git remote add origin https://github.com/SurehSan/ltc-dashboard
git add . && git commit -m "initial build"
git push -u origin main

# 2. Deploy on Streamlit Community Cloud
# → share.streamlit.io → Connect GitHub repo → app.py as entry point

# 3. Point surehsan.com subdomain
# → Add CNAME: dashboard.surehsan.com → your-app.streamlit.app
# → Configure in Cloudflare Pages DNS
```

---

## 8. Requirements

```txt
streamlit==1.35.0
pandas==2.2.2
numpy==1.26.4
plotly==5.22.0
matplotlib==3.9.0
duckdb==0.10.3
sqlalchemy==2.0.30
```

---

## 9. README Framing (Actuarial Language)

```markdown
## LTC Cost & Mortality Risk Dashboard

Actuarial cost projection tool for long-term care facilities. Models present value 
of future care costs by age cohort using SOA IAM mortality tables, CMS nursing home 
data, and CDC WONDER mortality rates.

**Key outputs:**
- Present value of expected LTC costs from resident entry age
- Cohort-specific survival probability curves (qx, lx, ex)
- Sensitivity analysis across discount rate, inflation rate, and care level
- Facility break-even occupancy threshold modeling

**Data sources:** SOA IAM 2012, CMS Provider Data, CDC WONDER  
**Methods:** Life table construction, time value of money, contribution margin analysis  
**Stack:** Python (pandas, numpy, plotly), SQLite, Streamlit, Tableau Public / Power BI  
**Live demo:** dashboard.surehsan.com
```

---

## 10. Weekend Timeline

| Time Block | Task |
|---|---|
| Saturday AM | Download + clean CDC, CMS, SOA data → `data/raw/`; write `schema.sql`; load to SQLite via `db/load.py` |
| Saturday PM | Build `ingest.py`, `life_table.py`; write and test `sql/cohort_mortality.sql` and `sql/cost_projections.sql` in DB Browser for SQLite |
| Sunday AM | Build `cost_model.py`, `breakeven.py`; write `sql/breakeven_summary.sql`; unit test formulas |
| Sunday PM (early) | Build Tableau Public or Power BI report connected to SQLite/CSV outputs |
| Sunday PM (late) | Wire `app.py`, deploy to Streamlit Cloud, configure DNS, commit `.pbix`/`.twbx` to repo |

**Definition of done:** Live URL, clean README, pushed to GitHub — ready to paste into a job application as a portfolio link.

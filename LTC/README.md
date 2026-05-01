# LTC Cost & Mortality Risk Dashboard

Actuarial cost-projection tool for long-term care (LTC) facilities.
Models the present value of future care costs by age cohort using SOA
IAM mortality tables, CMS Nursing Home Compare data, and CDC WONDER
mortality rates, surfaced via a Streamlit dashboard with interactive
sensitivity controls.

**Live demo:** `dashboard.surehsan.com` (Streamlit Community Cloud)

---

## What it does

| Output | Used by an LTC operator for |
|---|---|
| Present value of expected future care costs by cohort | Pricing assisted-living contracts; insurance-reserve calculations |
| Survival probability curves (`qx`, `lx`, `ex`) | Estimating average length of stay per admission type |
| Sensitivity to inflation rate | Budgeting wage / supply / CPI cost increases |
| Sensitivity to discount rate | Capital planning, bond-issuance decisions |
| Break-even occupancy % | Minimum census needed to cover fixed overhead |

**Concrete example.** A 78-year-old admits to memory care at $8,500/mo.
Held to a 4.5% discount rate and 3.5% cost inflation, the model
projects the lifetime PV of expected care costs and decomposes it into
year-by-year contributions weighted by survival.

---

## Quickstart

```bash
git clone https://github.com/SurehSan/ltc-dashboard
cd ltc-dashboard

# 1. Environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Build the warehouse from raw CSVs
python -m src.ingest         # raw -> data/processed/
python -m db.load            # data/processed/ -> db/ltc.db

# 3. Run the dashboard
streamlit run app.py
```

The dashboard will open at <http://localhost:8501>.

---

## Project layout

```
ltc-dashboard/
├── app.py                  Streamlit entry point
├── requirements.txt
├── README.md
├── .gitignore
│
├── data/
│   ├── raw/                Source CSVs (CMS, CDC, SOA)
│   └── processed/          Cleaned outputs of src/ingest.py
│
├── db/
│   ├── schema.sql          SQLite DDL for the warehouse
│   ├── load.py             Rebuilds db/ltc.db from processed CSVs
│   └── ltc.db              Built artifact (gitignored)
│
├── sql/                    Analytical queries (run against db/ltc.db)
│   ├── cohort_mortality.sql
│   ├── cost_projections.sql
│   ├── breakeven_summary.sql
│   └── sensitivity_pv.sql
│
├── src/
│   ├── ingest.py           Load + clean raw data
│   ├── life_table.py       qx -> lx, dx, ex
│   ├── cost_model.py       PV of future care costs
│   ├── breakeven.py        CVP / occupancy break-even
│   └── utils.py            Paths and helpers
│
├── tableau/                Tableau & Power BI workbooks (BI layer)
├── tests/                  Unit tests (pytest)
└── docs/                   Methodology and data-dictionary write-ups
```

---

## Data sources

| Source | URL | Used for |
|---|---|---|
| **SOA IAM 2012** | <https://mort.soa.org/> | Industry-standard `qx`/`lx` for annuitant populations |
| **CMS Nursing Home Compare** | <https://data.cms.gov/provider-data/topics/nursing-homes> | Facility roster, beds, occupancy, ratings |
| **CDC WONDER** | <https://wonder.cdc.gov/> | Cross-check mortality rates by age band |

The CSVs in `data/raw/` are representative samples shaped like the
real exports — replace with live downloads when refreshing.

---

## Methods

### Life-table construction (`src/life_table.py`)

For an ordered series of one-year mortality probabilities `qx`:

```
lx[0]   = 100,000             (radix)
dx[t]   = lx[t] * qx[t]
lx[t+1] = lx[t] - dx[t]
ex[t]   = sum_{k>=1} (l_{t+k} / l_t)    # curtate life expectancy
```

### Present value of care costs (`src/cost_model.py`)

```
PV = sum_{t=0..T} [ C * (1 + i)^t * p_t ] / (1 + d)^t
```

where `C` is the year-zero annual cost, `i` is annual inflation, `d`
is the annual discount rate, and `p_t = lx[t] / lx[0]` is the
probability of surviving to year `t` from entry.

### Break-even occupancy (`src/breakeven.py`)

```
contribution_margin   = revenue_per_resident - variable_cost_per_resident
breakeven_residents   = fixed_costs_monthly / contribution_margin
breakeven_pct         = breakeven_residents / total_beds * 100
```

For the portfolio view, fixed costs are modeled as a share of
full-census revenue (default 45%), and variable costs scale with care
intensity (`independent_living` < `assisted_living` < `memory_care` <
`skilled_nursing`).

A more detailed walk-through lives in [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md).

---

## SQL warehouse

The pipeline materializes a single-file SQLite warehouse at
`db/ltc.db` with three tables:

- `mortality_rates`     — long-form `(age, sex, qx, lx, source)`
- `cost_projections`    — `(age_entry, care_level, year_t, ...)` rows
- `breakeven_summary`   — one row per facility with risk flag

The queries in `sql/` are the same ones a finance analyst would run
in DB Browser, Tableau, or Power BI on top of the warehouse. They
are also surfaced in the dashboard's "Warehouse peek" panel.

---

## BI layer (Tableau / Power BI)

The same SQLite database is the source of truth for an executive
dashboard built in either tool:

- **Tableau Public** — connect via SQLite ODBC driver, build the
  three sheets in `docs/BI_GUIDE.md`, publish to Tableau Public.
- **Power BI Desktop** — `Get Data → ODBC → SQLite3 Datasource`, then
  the matrix / line-chart / slicer setup in `docs/BI_GUIDE.md`.

A starter `.twbx` / `.pbix` is checked into `tableau/` once built.

---

## Stack

| Layer | Tool |
|---|---|
| Data processing | `pandas`, `numpy` |
| Actuarial math | `numpy` (vectorized) |
| Warehouse | SQLite (with DuckDB as a drop-in alternative) |
| Visualization | `plotly`, `matplotlib` |
| Dashboard | `streamlit` |
| BI reporting | Tableau Public, Power BI Desktop |
| Deployment | Streamlit Community Cloud |
| Version control | `git` + GitHub |

---

## Deployment

1. Push to GitHub.
2. Connect the repo on Streamlit Community Cloud
   (<https://share.streamlit.io>) and set `app.py` as the entry point.
3. In Cloudflare DNS for `surehsan.com`, add a CNAME for
   `dashboard.surehsan.com` pointing at the Streamlit-issued URL.

See [`docs/DEPLOY.md`](docs/DEPLOY.md) for the full walk-through.

---

## License

MIT. Synthetic data provided in `data/raw/` is illustrative only; do
not use for actuarial pricing without replacing with vendor- or
agency-sourced data.

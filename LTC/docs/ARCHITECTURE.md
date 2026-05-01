# Architecture

The pipeline is a three-stage feed-forward graph: raw → processed →
warehouse → presentation. Each stage is idempotent and can be
re-run independently.

```
data/raw/*.csv
   |
   |  src.ingest.build_processed_inputs()
   v
data/processed/*.csv
   |
   |  db.load.main()
   v
db/ltc.db  ──────────────────────────┐
   ^                                 |
   |                                 |  read-only consumers:
   | src.life_table /                |   - app.py        (Streamlit)
   | src.cost_model /                |   - sql/*.sql     (BI tools)
   | src.breakeven                   |   - tableau/*     (Tableau / Power BI)
   |                                 |
   └─ in-memory transformations ─────┘
```

---

## Stage 1 — Ingest (`src/ingest.py`)

Pure I/O + light cleaning.

- `load_soa_table()` — SOA IAM mortality CSV → tidy DataFrame
- `load_cdc_mortality()` — CDC WONDER tab-delimited export → DataFrame
- `load_cms_nursing_home()` — CMS roster CSV → DataFrame
- `build_processed_inputs()` — orchestrator: writes
  `data/processed/survival_table.csv` and
  `data/processed/cms_facilities.csv`

Inputs are versioned in git; outputs are gitignored because they
are deterministic functions of the inputs.

---

## Stage 2 — Modeling (`src/life_table.py`, `src/cost_model.py`, `src/breakeven.py`)

Pure functions over DataFrames or scalars. No I/O. No side effects.

- **`life_table.build_life_table(qx_series, ...)`** → life table
- **`cost_model.pv_future_costs(...)`** → scalar PV
- **`cost_model.cost_projection_table(...)`** → year-by-year DataFrame
- **`breakeven.breakeven_occupancy(...)`** → dict for one facility
- **`breakeven.facility_breakeven_table(...)`** → DataFrame across the
  portfolio

The Streamlit app and the warehouse loader both call these directly
— the loader to materialize results into SQLite, the app to compute
on the fly with whatever the user typed into the sidebar.

---

## Stage 3 — Warehouse (`db/`)

`db/load.py` rebuilds `db/ltc.db` from the processed CSVs:

1. Drop and recreate all tables via `db/schema.sql`.
2. Load `mortality_rates` from `survival_table.csv`.
3. Compute the `cost_projections` grid (entry-age × care-level) and
   load it.
4. Compute `breakeven_summary` over the CMS roster and load it.

The DB is intentionally treated as a built artifact, not a source
of truth. It is **never** edited by hand; every change goes through
re-running the loader.

---

## Stage 4 — Presentation

Three independent consumers all read the same warehouse:

- `app.py` (Streamlit) — primary interactive surface
- `sql/*.sql` — analytical queries that produce DataFrames or BI extracts
- `tableau/*.twbx` / `*.pbix` — executive-facing dashboards

If you want to swap consumers (say, replace Streamlit with Dash),
nothing in stages 1–3 needs to change.

---

## Why SQLite, not Postgres or BigQuery

- **Single-file artifact.** The whole warehouse fits in `db/ltc.db`,
  no server, no auth, no network round-trip.
- **Tableau / Power BI compatible.** Both accept SQLite via ODBC.
- **DuckDB drop-in.** For larger CMS extracts, switch to DuckDB by
  changing `sqlite3.connect(...)` to `duckdb.connect(...)` — same
  SQL, no schema changes.
- **Reproducible.** Anyone can clone the repo, run two commands,
  and rebuild every byte of the warehouse.

For a real production deploy at a senior-living operator, you would
swap SQLite for Postgres (or Snowflake) and add an Airflow DAG. The
shape of the pipeline above does not change.

---

## Idempotency contract

- Re-running `src.ingest.build_processed_inputs()` overwrites
  `data/processed/`.
- Re-running `db.load.main()` drops and recreates every table in
  `db/ltc.db`.
- Both are safe to call any number of times in any order.

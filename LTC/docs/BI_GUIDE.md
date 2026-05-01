# BI Layer — Tableau & Power BI

The Streamlit dashboard is the developer-facing surface. The BI
layer is the executive-facing surface that sits on top of the same
SQLite warehouse (`db/ltc.db`). Build one of the two; both connect
to the same database and reproduce the same numbers.

---

## Tableau Public

1. Download Tableau Public (free): <https://public.tableau.com/>
2. Install the SQLite ODBC driver (Christian Werner's build is the
   canonical one): <http://www.ch-werner.de/sqliteodbc/>
3. In Tableau: `Connect → Other Databases (ODBC)` and point at
   `db/ltc.db`. Alternatively, connect to `data/processed/*.csv`
   and skip the driver — fine for the weekend version.
4. Build these three sheets:

| Sheet | Chart | Fields |
|---|---|---|
| **Survival curves** | Line | `age` (cols), `lx` (rows), `sex` (color) |
| **PV cost by cohort** | Bar | `age_entry` (cols), `SUM(pv_cost)` (rows), `care_level` (color) |
| **Census risk** | Highlight table | `facility_name` (rows), `breakeven_pct` (text + color), `census_risk_flag` (color stop) |

5. Assemble into a dashboard titled **"LTC Cost & Mortality Risk —
   Actuarial Summary"**.
6. `Server → Tableau Public → Save to Tableau Public`. Copy the
   embed URL into `surehsan.com`.

---

## Power BI Desktop

1. Download Power BI Desktop (free):
   <https://powerbi.microsoft.com/desktop>
2. `Get Data → Text/CSV` → load
   - `data/processed/cms_facilities.csv`
   - the export of `sql/cost_projections.sql` (run it from DB
     Browser for SQLite or via `python -m db.load`, then export
     the table as CSV).
   - the export of `sql/breakeven_summary.sql`.
3. In Power Query, add a calculated column for the risk flag if not
   already present:

   ```text
   census_risk_flag =
     IF([breakeven_pct] > 90, "HIGH RISK",
       IF([breakeven_pct] >= 80, "WATCH", "STABLE"))
   ```

4. Build a single-page report with:
   - **Card visuals** — Avg PV cost, Avg break-even %, Total cohorts
   - **Line chart** — Survival probability by age and care level
   - **Matrix** — Entry age × Care level → Total PV cost (heatmap formatting)
   - **Slicers** — Discount-rate band, Inflation-rate band

5. Save to `tableau/ltc_dashboard.pbix` and commit.

---

## Connecting Power BI directly to SQLite (recommended)

This is the configuration enterprise analysts actually use and is
worth highlighting in the README:

```
Get Data → ODBC → DSN: SQLite3 Datasource
Connection string: Driver={SQLite3 ODBC Driver};Database=db/ltc.db
```

Then write **DirectQuery** views against the SQL files in `sql/` so
the report stays a thin presentation layer over the warehouse.

---

## Visual style notes

Keep the executive view to 5 visuals or fewer. The Streamlit app is
the "drill-in" tool; the BI layer is the one-pager. Aim for:

- One headline number (avg PV cost across the portfolio).
- One time-series (survival or expected cost).
- One geographic / hierarchical slice (state × care level).
- One risk table (census risk flag, sorted by `breakeven_pct`).

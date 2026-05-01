# Data Dictionary

Every column in `data/raw/`, `data/processed/`, and `db/ltc.db`,
with units, source, and a one-line definition.

---

## `data/raw/soa_iam_2012.csv`

| Column | Type | Unit | Definition |
|---|---|---|---|
| `age` | int | years | Exact age in whole years (65–100) |
| `sex` | str | — | `M` or `F` |
| `qx` | float | probability | One-year probability of death at age `x` |
| `lx` | int | persons | Number of survivors at age `x` (radix = 100,000) |
| `source` | str | — | Always `SOA_IAM_2012` |

Source: SOA IAM 2012 Basic Table (representative values).

---

## `data/raw/cdc_mortality.csv`

Tab-delimited, with a 15-line metadata footer (skipped by the
loader). Mirrors the export layout of CDC WONDER UCD.

| Column | Type | Unit | Definition |
|---|---|---|---|
| `Notes` | str | — | Always blank for data rows; used as a row-level annotation column by WONDER |
| `Age Group` | str | — | Five-year age band, e.g. `65-69` |
| `Age Group Code` | str | — | WONDER's grouping code |
| `Deaths` | int | persons | Aggregated deaths in the band |
| `Population` | int | persons | Mid-period population estimate |
| `Crude Rate` | float | per 100,000 | Deaths × 100,000 / Population |

Source: CDC WONDER, Underlying Cause of Death (representative
sample). For actuarial use, divide `Crude Rate` by 100,000 to get a
band-level `qx`.

---

## `data/raw/cms_nursing_home.csv`

| Column | Type | Unit | Definition |
|---|---|---|---|
| `facility_id` | str | — | Synthetic facility identifier |
| `facility_name` | str | — | Display name |
| `state` | str | — | Two-letter US state code |
| `total_beds` | int | beds | Licensed bed capacity |
| `occupancy_pct` | float | % | Reported average occupancy |
| `avg_length_of_stay_days` | int | days | Average length of stay per admission |
| `overall_rating` | int | 1–5 stars | CMS Five-Star Quality Rating |
| `staffing_rating` | int | 1–5 stars | Staffing component of the Five-Star rating |
| `quality_rating` | int | 1–5 stars | Quality-measures component of the Five-Star rating |
| `care_type` | str | — | One of `independent_living`, `assisted_living`, `memory_care`, `skilled_nursing` |

Source: CMS Nursing Home Compare (representative sample).

---

## `data/processed/survival_table.csv`

Same shape and units as `data/raw/soa_iam_2012.csv` after light
cleaning (column lowercased, age range filter, sort by sex+age).

---

## `data/processed/cms_facilities.csv`

Same shape and units as `data/raw/cms_nursing_home.csv` after light
cleaning (column lowercased, NaN drops on bed count and care type).

---

## `db/ltc.db` — `mortality_rates`

| Column | Type | Unit | Definition |
|---|---|---|---|
| `age` | INTEGER | years | Exact age |
| `sex` | TEXT | — | `M` or `F` |
| `qx` | REAL | probability | One-year probability of death |
| `lx` | REAL | persons | Survivors at age `x` from radix 100,000 |
| `source` | TEXT | — | Provenance tag (`SOA_IAM_2012`) |

---

## `db/ltc.db` — `cost_projections`

| Column | Type | Unit | Definition |
|---|---|---|---|
| `age_entry` | INTEGER | years | Entry age of the cohort |
| `care_level` | TEXT | — | Care-level key matching `cost_model.CARE_COSTS` |
| `year_t` | INTEGER | years | Years from entry; `0` is the entry year |
| `age_at_t` | INTEGER | years | `age_entry + year_t` |
| `survival_prob` | REAL | probability | `lx[t] / lx[0]`, the unconditional probability of being alive in year `t` |
| `expected_cost` | REAL | USD | Inflation-adjusted, survival-weighted cash flow |
| `pv_cost` | REAL | USD | `expected_cost / (1 + d)^t` |
| `discount_rate` | REAL | decimal | `d` used to compute the row |
| `inflation_rate` | REAL | decimal | `i` used to compute the row |

The default load uses `d = 0.045`, `i = 0.035`, female SOA IAM
survival, and entry ages `{65, 70, 75, 78, 80, 85}` × the four
care levels.

---

## `db/ltc.db` — `breakeven_summary`

| Column | Type | Unit | Definition |
|---|---|---|---|
| `facility_id` | TEXT | — | Joins to `cms_facilities.facility_id` |
| `facility_name` | TEXT | — | Display name |
| `state` | TEXT | — | Two-letter US state |
| `care_type` | TEXT | — | Care level used to look up revenue and variable cost |
| `total_beds` | INTEGER | beds | Licensed capacity |
| `occupancy_pct` | REAL | % | Reported occupancy from the CMS feed |
| `fixed_costs` | REAL | USD/month | Modeled fixed monthly overhead (`revenue_per_bed · beds · ratio`) |
| `revenue_per_bed` | REAL | USD/month | Revenue per occupied bed (from `cost_model.CARE_COSTS`) |
| `variable_per_bed` | REAL | USD/month | Variable cost per occupied bed (from `breakeven.VARIABLE_COSTS`) |
| `breakeven_residents` | REAL | residents | Census needed to cover fixed costs |
| `breakeven_pct` | REAL | % | `breakeven_residents / total_beds · 100` |
| `contribution_margin` | REAL | USD/month | `revenue_per_bed − variable_per_bed` |
| `census_risk_flag` | TEXT | — | One of `STABLE`, `WATCH`, `HIGH RISK`, or `UNDEFINED` |

---

## Cross-references

- `cost_projections.care_level` ⟵ keys of `cost_model.CARE_COSTS`
- `breakeven_summary.care_type` ⟵ keys of `cost_model.CARE_COSTS` *and* `breakeven.VARIABLE_COSTS`
- `mortality_rates.(age, sex)` is the primary lookup the life-table builder uses

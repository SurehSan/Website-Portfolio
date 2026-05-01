# Methodology

This document covers the actuarial reasoning behind each module in the
LTC dashboard. The goal is for an actuarial analyst (or a finance
recruiter) to be able to reproduce every number the dashboard shows
from the formulas below and the raw CSVs.

---

## 1. Notation

| Symbol | Definition |
|---|---|
| `x` | Exact age in whole years |
| `qx` | One-year probability of death given alive at age `x` |
| `px` | One-year probability of survival, `1 − qx` |
| `lx` | Number of survivors at age `x` from a starting cohort (the *radix*, conventionally 100,000) |
| `dx` | Expected deaths between ages `x` and `x+1`, equal to `lx · qx` |
| `ex` | Curtate life expectancy at age `x`, expected whole years of life remaining |
| `p_t` | Probability of surviving to year `t` from entry, `lx[t] / lx[0]` |
| `i` | Annual cost inflation, decimal |
| `d` | Annual discount rate, decimal |
| `C` | Year-zero monthly cost; annual cost is `12 · C` |

---

## 2. Life table

Given an ordered series of `qx` values, construct:

```
lx[0]   = radix                             # default 100,000
dx[t]   = lx[t] · qx[t]
lx[t+1] = lx[t] − dx[t]
```

Curtate life expectancy at the first age in the table:

```
e[t] = sum_{k=1..K} (l[t+k] / l[t])
```

where `K = len(table) − t − 1`. We use **curtate** (whole-year)
expectancy because it pairs naturally with annual cost integration
in the PV step. Complete (mid-year) expectancy adds `0.5` and is
quoted in life-insurance contexts but does not affect the PV we
compute.

The implementation in `src/life_table.py` is the deterministic
forward recursion above; no smoothing or graduation is applied
because the SOA IAM table is already published as a graduated
table.

---

## 3. Present value of care costs

For an entrant at age `x_0` with monthly cost `C`:

```
PV = Σ_{t=0..T}  [ 12·C · (1+i)^t · p_t ]   /   (1+d)^t
```

This is the standard PV of a continuing-care annuity with mortality
decrements applied to each year's cash flow. Three things to note:

1. **Inflation and discount move independently.** They are not
   collapsed into a "real rate" because the dashboard's whole point
   is sensitivity testing across both axes.
2. **`p_t` is unconditional.** It is the probability of surviving
   from entry to year `t`, not the conditional probability of
   surviving year `t` given alive at `t−1`.
3. **First-year cash flow is undiscounted.** Year `t = 0` contributes
   `12·C · 1 · 1 = 12·C` because `p_0 = 1` and `(1+d)^0 = 1`. This
   matches the actuarial convention of paying the first annuity
   instalment at issue.

Year-by-year decomposition (`src/cost_model.cost_projection_table`)
returns the per-year `expected_cost` (numerator) and `pv_cost`
(after discounting), which together produce the area chart in the
dashboard and the `cost_projections` warehouse table.

---

## 4. Sensitivity grid

The grid in the dashboard varies `d` and `i` over a 5×5 lattice
(2%–6% by 1%, both axes). Each cell re-runs the PV calculation
holding the cohort, sex, care level, and monthly cost fixed.

**Why this matters operationally.** A treasurer setting reserve
levels needs to know how much PV moves under a 100bp shift in
either parameter. The diagonal of the grid (where `d ≈ i`) is the
"real-rate-zero" line and tends to track raw years-of-life-remaining
× cost.

---

## 5. Break-even occupancy (CVP)

For one facility:

```
margin   = revenue_per_resident − variable_cost_per_resident
beds_be  = fixed_costs_monthly / margin
pct_be   = beds_be / total_beds · 100
```

Risk classification:

| Bucket | `pct_be` |
|---|---|
| HIGH RISK | > 90% |
| WATCH | 80–90% |
| STABLE | < 80% |

The single-facility calculator in the dashboard accepts arbitrary
inputs. The portfolio-level view (`facility_breakeven_table`) makes
two assumptions to keep the inputs to the CMS roster minimal:

- **Fixed costs scale with full-census revenue.** Default
  `fixed_cost_ratio = 0.45` puts monthly overhead at 45% of
  rate-card revenue at full occupancy. This produces break-even
  thresholds in the realistic 65–90% band across care levels.
- **Variable costs scale with care intensity.** Independent living
  is mostly food and utilities; skilled nursing adds direct nursing
  labor and pharmacy. The default vector is in
  `breakeven.VARIABLE_COSTS`.

Both assumptions are exposed as kwargs so an analyst can override
them with facility-level data when available.

---

## 6. Why SOA, not CDC, for pricing

CDC WONDER mortality is *crude*: deaths divided by the general
population in a band. It includes everyone — including residents
who never had access to the kind of care the dashboard is pricing.
Annuitant populations (SOA IAM) have lower mortality at every age
because they are a self-selected, healthier-than-average slice of
the population.

For dashboarding, using CDC overstates `qx`, understates `lx`, and
**under**states PV. The right call for any pricing-adjacent use is
SOA. CDC data is loaded for cross-check and band-level reasoning
only.

---

## 7. Reproducibility

Every number in the dashboard can be reproduced by:

1. Reading the corresponding CSV in `data/raw/`.
2. Running the formula above with the parameters shown in the UI.
3. Matching against the row in `db/ltc.db` (queryable via the SQL
   files in `sql/`).

The pipeline is deterministic — the warehouse can be deleted at any
time and rebuilt with `python -m db.load`.

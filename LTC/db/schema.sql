-- LTC Cost & Mortality Risk Dashboard
-- SQLite schema for the analytical warehouse layer.
--
-- All three tables are populated by db/load.py from the processed CSVs
-- in data/processed/. Drop and rebuild from scratch on every load to
-- keep the warehouse a deterministic function of raw inputs.

-- ---------------------------------------------------------------
-- mortality_rates
-- One row per (age, sex) with the one-year death probability qx.
-- Source is preserved so we can mix SOA and CDC views downstream.
-- ---------------------------------------------------------------
DROP TABLE IF EXISTS mortality_rates;
CREATE TABLE mortality_rates (
    age      INTEGER NOT NULL,
    sex      TEXT,
    qx       REAL    NOT NULL,    -- one-year probability of death at age x
    lx       REAL,                 -- survivors at age x (radix = 100,000 in SOA tables)
    source   TEXT    DEFAULT 'SOA' -- 'SOA' | 'CDC'
);

CREATE INDEX IF NOT EXISTS idx_mortality_age      ON mortality_rates (age);
CREATE INDEX IF NOT EXISTS idx_mortality_age_sex  ON mortality_rates (age, sex);

-- ---------------------------------------------------------------
-- cost_projections
-- Year-by-year (entry age × care level) projection of expected and
-- discounted costs. One row per future year of the cohort's life.
-- ---------------------------------------------------------------
DROP TABLE IF EXISTS cost_projections;
CREATE TABLE cost_projections (
    age_entry      INTEGER NOT NULL,
    care_level     TEXT    NOT NULL,
    year_t         INTEGER NOT NULL,    -- years from entry (0 = entry year)
    age_at_t       INTEGER NOT NULL,
    survival_prob  REAL    NOT NULL,    -- p_t in the PV formula
    expected_cost  REAL    NOT NULL,    -- inflated, survival-weighted, undiscounted
    pv_cost        REAL    NOT NULL,    -- expected_cost / (1+d)^t
    discount_rate  REAL    NOT NULL,
    inflation_rate REAL    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_costproj_cohort
    ON cost_projections (age_entry, care_level);

-- ---------------------------------------------------------------
-- breakeven_summary
-- Per-facility CVP output. One row per CMS-listed facility.
-- ---------------------------------------------------------------
DROP TABLE IF EXISTS breakeven_summary;
CREATE TABLE breakeven_summary (
    facility_id          TEXT    PRIMARY KEY,
    facility_name        TEXT,
    state                TEXT,
    care_type            TEXT,
    total_beds           INTEGER,
    occupancy_pct        REAL,
    fixed_costs          REAL,
    revenue_per_bed      REAL,
    variable_per_bed     REAL,
    breakeven_residents  REAL,
    breakeven_pct        REAL,
    contribution_margin  REAL,
    census_risk_flag     TEXT
);

CREATE INDEX IF NOT EXISTS idx_breakeven_state ON breakeven_summary (state);
CREATE INDEX IF NOT EXISTS idx_breakeven_risk  ON breakeven_summary (census_risk_flag);

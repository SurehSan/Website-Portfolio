-- breakeven_summary.sql
-- Facility-level census risk view.
-- Sorts highest-risk facilities first so the BI consumer's first row
-- is always the one most likely to need attention.

SELECT
    facility_id,
    facility_name,
    state,
    care_type,
    total_beds,
    ROUND(occupancy_pct, 1)           AS occupancy_pct,
    ROUND(breakeven_pct, 1)           AS breakeven_pct,
    ROUND(contribution_margin, 2)     AS contribution_margin,
    CASE
        WHEN breakeven_pct > 90 THEN 'HIGH RISK'
        WHEN breakeven_pct >= 80 THEN 'WATCH'
        ELSE 'STABLE'
    END                               AS census_risk_flag,
    -- "Cushion" = how many percentage points of slack between current
    -- census and break-even. Negative means the facility is below break-even.
    ROUND(occupancy_pct - breakeven_pct, 1) AS occupancy_cushion_pct
FROM breakeven_summary
ORDER BY breakeven_pct DESC;

-- cost_projections.sql
-- Total PV of expected care costs by entry age and care level.
-- This is the headline summary a finance VP wants — one row per
-- cohort with the lifetime PV, average survival, and cohort length.

SELECT
    age_entry,
    care_level,
    ROUND(SUM(pv_cost), 2)            AS total_pv_cost,
    ROUND(SUM(expected_cost), 2)      AS total_expected_cost,
    ROUND(AVG(survival_prob), 4)      AS avg_survival_prob,
    COUNT(*)                          AS projection_years,
    MAX(discount_rate)                AS discount_rate,
    MAX(inflation_rate)               AS inflation_rate
FROM cost_projections
GROUP BY age_entry, care_level
ORDER BY age_entry, care_level;

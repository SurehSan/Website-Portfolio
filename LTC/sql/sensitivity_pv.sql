-- sensitivity_pv.sql
-- Lifetime PV of memory care for a 78-year-old, year by year.
-- A worked example used in the dashboard's "explainer" panel — drop
-- the WHERE clause to expand to all cohorts.

SELECT
    age_entry,
    age_at_t,
    year_t,
    ROUND(survival_prob, 4)   AS survival_prob,
    ROUND(expected_cost, 2)   AS expected_cost,
    ROUND(pv_cost, 2)         AS pv_cost,
    ROUND(SUM(pv_cost) OVER (
        PARTITION BY age_entry, care_level
        ORDER BY year_t
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2)                     AS cumulative_pv
FROM cost_projections
WHERE age_entry = 78
  AND care_level = 'memory_care'
ORDER BY year_t;

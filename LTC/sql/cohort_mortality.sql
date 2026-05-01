-- cohort_mortality.sql
-- Average qx and band size by 5-year age band.
-- Used in the dashboard's mortality summary and as the input for any
-- BI tool that wants pre-aggregated mortality.

SELECT
    (age / 5) * 5                    AS age_band_start,
    (age / 5) * 5 + 4                AS age_band_end,
    sex                              AS sex,
    ROUND(AVG(qx), 5)                AS avg_qx,
    COUNT(*)                         AS ages_in_band
FROM mortality_rates
WHERE age BETWEEN 65 AND 100
GROUP BY age_band_start, sex
ORDER BY sex, age_band_start;

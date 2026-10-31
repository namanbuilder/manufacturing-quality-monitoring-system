-- Analytical SQL queries powering the dashboard (SQLite dialect).
-- The app runs filtered variants of these, adding a WHERE built from the
-- sidebar filters. Named blocks are parsed by src/db.py (`-- name:` markers).

-- name: overall_kpis
SELECT
    COUNT(*)                                          AS total_inspected,
    SUM(status = 'Fail')                              AS total_defects,
    ROUND(100.0 * SUM(status = 'Fail') / COUNT(*), 2) AS defect_rate_pct
FROM inspections;

-- name: defect_rate_by_line
SELECT
    production_line,
    COUNT(*)                                          AS inspected,
    SUM(status = 'Fail')                              AS defects,
    ROUND(100.0 * SUM(status = 'Fail') / COUNT(*), 2) AS defect_rate_pct
FROM inspections
GROUP BY production_line
ORDER BY defect_rate_pct DESC;

-- name: defect_rate_by_shift
SELECT
    shift,
    ROUND(100.0 * SUM(status = 'Fail') / COUNT(*), 2) AS defect_rate_pct
FROM inspections
GROUP BY shift
ORDER BY defect_rate_pct DESC;

-- name: defect_rate_by_product
SELECT
    product_model,
    ROUND(100.0 * SUM(status = 'Fail') / COUNT(*), 2) AS defect_rate_pct
FROM inspections
GROUP BY product_model
ORDER BY defect_rate_pct DESC;

-- name: monthly_trend
SELECT
    strftime('%Y-%m', date)                           AS month,
    ROUND(100.0 * SUM(status = 'Fail') / COUNT(*), 2) AS defect_rate_pct
FROM inspections
GROUP BY month
ORDER BY month;

-- name: pareto_defect_types
SELECT
    defect_type,
    COUNT(*)                                            AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)  AS pct,
    ROUND(100.0 * SUM(COUNT(*)) OVER (ORDER BY COUNT(*) DESC)
                 / SUM(COUNT(*)) OVER (), 2)            AS cumulative_pct
FROM inspections
WHERE status = 'Fail'
GROUP BY defect_type
ORDER BY count DESC;

-- name: severity_breakdown
SELECT severity, COUNT(*) AS count
FROM inspections
WHERE status = 'Fail'
GROUP BY severity
ORDER BY CASE severity WHEN 'Critical' THEN 1 WHEN 'Major' THEN 2 ELSE 3 END;

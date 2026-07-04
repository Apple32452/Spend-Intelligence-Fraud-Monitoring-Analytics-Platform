WITH monthly_employee_spend AS (
    SELECT
        DATE_TRUNC('month', t.transaction_timestamp) AS spend_month,
        t.employee_id,
        t.company_id,
        SUM(
            CASE
                WHEN t.transaction_status = 'approved' THEN t.amount
                ELSE 0
            END
        ) AS monthly_spend
    FROM transactions AS t
    GROUP BY 1, 2, 3
),

employee_budget_risk AS (
    SELECT
        mes.spend_month,
        mes.company_id,
        mes.employee_id,
        e.employee_name,
        e.department,
        e.monthly_budget,
        ROUND(mes.monthly_spend, 2) AS monthly_spend,
        ROUND(
            100.0 * mes.monthly_spend / e.monthly_budget,
            2
        ) AS budget_used_pct,
        ROUND(
            mes.monthly_spend - e.monthly_budget,
            2
        ) AS budget_overage
    FROM monthly_employee_spend AS mes
    JOIN employees AS e
        ON mes.employee_id = e.employee_id
)

SELECT
    spend_month,
    company_id,
    employee_id,
    employee_name,
    department,
    monthly_budget,
    monthly_spend,
    budget_used_pct,
    budget_overage,
    CASE
        WHEN budget_used_pct >= 100 THEN 'over_budget'
        WHEN budget_used_pct >= 80 THEN 'at_risk'
        ELSE 'within_budget'
    END AS budget_status
FROM employee_budget_risk
WHERE budget_used_pct >= 80
ORDER BY
    spend_month DESC,
    budget_used_pct DESC;

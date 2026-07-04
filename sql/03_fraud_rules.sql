WITH employee_transaction_stats AS (
    SELECT
        employee_id,
        AVG(amount) AS employee_avg_amount,
        STDDEV_POP(amount) AS employee_amount_stddev
    FROM transactions
    WHERE transaction_status = 'approved'
    GROUP BY employee_id
),

transaction_features AS (
    SELECT
        t.transaction_id,
        t.company_id,
        t.employee_id,
        e.employee_name,
        t.merchant_id,
        m.merchant_name,
        m.category,
        t.transaction_timestamp,
        t.amount,
        t.is_international,
        t.merchant_country,
        ets.employee_avg_amount,
        ets.employee_amount_stddev,
        COUNT(*) OVER (
            PARTITION BY t.employee_id
            ORDER BY t.transaction_timestamp
            RANGE BETWEEN INTERVAL 10 MINUTE PRECEDING
                  AND CURRENT ROW
        ) AS transactions_last_10_minutes
    FROM transactions AS t
    JOIN employees AS e
        ON t.employee_id = e.employee_id
    JOIN merchants AS m
        ON t.merchant_id = m.merchant_id
    JOIN employee_transaction_stats AS ets
        ON t.employee_id = ets.employee_id
    WHERE t.transaction_status = 'approved'
),

fraud_alerts AS (
    SELECT
        *,
        CASE
            WHEN amount >= 5000 THEN 1
            ELSE 0
        END AS large_transaction_flag,

        CASE
            WHEN employee_amount_stddev > 0
             AND amount > employee_avg_amount + 3 * employee_amount_stddev
            THEN 1
            ELSE 0
        END AS unusual_amount_flag,

        CASE
            WHEN transactions_last_10_minutes >= 4 THEN 1
            ELSE 0
        END AS velocity_flag,

        CASE
            WHEN is_international = TRUE
             AND amount >= 1000
            THEN 1
            ELSE 0
        END AS international_risk_flag
    FROM transaction_features
)

SELECT
    transaction_id,
    company_id,
    employee_id,
    employee_name,
    merchant_name,
    category,
    transaction_timestamp,
    amount,
    is_international,
    merchant_country,
    ROUND(employee_avg_amount, 2) AS employee_avg_amount,
    ROUND(employee_amount_stddev, 2) AS employee_amount_stddev,
    transactions_last_10_minutes,
    large_transaction_flag,
    unusual_amount_flag,
    velocity_flag,
    international_risk_flag,
    large_transaction_flag
        + unusual_amount_flag
        + velocity_flag
        + international_risk_flag AS fraud_risk_score,
    CASE
        WHEN large_transaction_flag
           + unusual_amount_flag
           + velocity_flag
           + international_risk_flag >= 2
        THEN 'high_risk'
        WHEN large_transaction_flag
           + unusual_amount_flag
           + velocity_flag
           + international_risk_flag = 1
        THEN 'medium_risk'
        ELSE 'low_risk'
    END AS fraud_risk_level
FROM fraud_alerts
WHERE large_transaction_flag
   + unusual_amount_flag
   + velocity_flag
   + international_risk_flag >= 1
ORDER BY fraud_risk_score DESC, amount DESC;

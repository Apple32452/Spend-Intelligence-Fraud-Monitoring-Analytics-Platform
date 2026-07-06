WITH employee_transaction_stats AS (
    SELECT
        employee_id,
        AVG(amount) AS employee_avg_amount,
        STDDEV_POP(amount) AS employee_amount_stddev
    FROM transactions
    WHERE transaction_status = 'approved'
    GROUP BY employee_id
),

ordered_transactions AS (
    SELECT
        t.transaction_id,
        t.employee_id,
        t.transaction_timestamp,
        LAG(t.transaction_timestamp) OVER (
            PARTITION BY t.employee_id
            ORDER BY t.transaction_timestamp
        ) AS previous_transaction_timestamp
    FROM transactions AS t
    WHERE t.transaction_status = 'approved'
),

burst_boundaries AS (
    SELECT
        *,
        CASE
            WHEN previous_transaction_timestamp IS NULL THEN 1
            WHEN transaction_timestamp
                 > previous_transaction_timestamp + INTERVAL 10 MINUTE
            THEN 1
            ELSE 0
        END AS starts_new_burst
    FROM ordered_transactions
),

burst_groups AS (
    SELECT
        *,
        SUM(starts_new_burst) OVER (
            PARTITION BY employee_id
            ORDER BY transaction_timestamp
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS burst_id
    FROM burst_boundaries
),

burst_sizes AS (
    SELECT
        employee_id,
        burst_id,
        COUNT(*) AS transactions_in_burst
    FROM burst_groups
    GROUP BY 1, 2
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
        bs.transactions_in_burst
    FROM transactions AS t
    JOIN employees AS e
        ON t.employee_id = e.employee_id
    JOIN merchants AS m
        ON t.merchant_id = m.merchant_id
    JOIN employee_transaction_stats AS ets
        ON t.employee_id = ets.employee_id
    JOIN burst_groups AS bg
        ON t.transaction_id = bg.transaction_id
    JOIN burst_sizes AS bs
        ON bg.employee_id = bs.employee_id
        AND bg.burst_id = bs.burst_id
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
             AND amount > employee_avg_amount
                 + 3 * employee_amount_stddev
            THEN 1
            ELSE 0
        END AS unusual_amount_flag,

        CASE
            WHEN transactions_in_burst >= 3 THEN 1
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
    transactions_in_burst,
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

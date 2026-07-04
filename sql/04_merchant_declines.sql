WITH merchant_transaction_metrics AS (
    SELECT
        m.merchant_id,
        m.merchant_name,
        m.category,
        m.country AS merchant_country,
        COUNT(*) AS total_transactions,
        SUM(
            CASE
                WHEN t.transaction_status = 'approved' THEN 1
                ELSE 0
            END
        ) AS approved_transactions,
        SUM(
            CASE
                WHEN t.transaction_status = 'declined' THEN 1
                ELSE 0
            END
        ) AS declined_transactions,
        ROUND(SUM(t.amount), 2) AS total_transaction_value,
        ROUND(
            AVG(
                CASE
                    WHEN t.transaction_status = 'approved' THEN t.amount
                END
            ),
            2
        ) AS avg_approved_transaction_amount
    FROM transactions AS t
    JOIN merchants AS m
        ON t.merchant_id = m.merchant_id
    GROUP BY 1, 2, 3, 4
),

decline_reason_metrics AS (
    SELECT
        m.merchant_id,
        t.decline_reason,
        COUNT(*) AS decline_count
    FROM transactions AS t
    JOIN merchants AS m
        ON t.merchant_id = m.merchant_id
    WHERE t.transaction_status = 'declined'
    GROUP BY 1, 2
),

top_decline_reason AS (
    SELECT
        merchant_id,
        decline_reason AS most_common_decline_reason,
        decline_count,
        ROW_NUMBER() OVER (
            PARTITION BY merchant_id
            ORDER BY decline_count DESC, decline_reason
        ) AS reason_rank
    FROM decline_reason_metrics
)

SELECT
    mtm.merchant_id,
    mtm.merchant_name,
    mtm.category,
    mtm.merchant_country,
    mtm.total_transactions,
    mtm.approved_transactions,
    mtm.declined_transactions,
    ROUND(
        100.0 * mtm.approved_transactions / mtm.total_transactions,
        2
    ) AS approval_rate_pct,
    ROUND(
        100.0 * mtm.declined_transactions / mtm.total_transactions,
        2
    ) AS decline_rate_pct,
    mtm.total_transaction_value,
    mtm.avg_approved_transaction_amount,
    tdr.most_common_decline_reason,
    CASE
        WHEN 100.0 * mtm.declined_transactions / mtm.total_transactions >= 12
        THEN 'high_decline_risk'
        WHEN 100.0 * mtm.declined_transactions / mtm.total_transactions >= 8
        THEN 'monitor'
        ELSE 'healthy'
    END AS merchant_payment_health
FROM merchant_transaction_metrics AS mtm
LEFT JOIN top_decline_reason AS tdr
    ON mtm.merchant_id = tdr.merchant_id
    AND tdr.reason_rank = 1
ORDER BY decline_rate_pct DESC, total_transactions DESC;

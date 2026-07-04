SELECT
    DATE_TRUNC('month', transaction_timestamp) AS transaction_month,
    COUNT(*) AS transaction_count,
    ROUND(SUM(amount), 2) AS total_spend,
    ROUND(AVG(amount), 2) AS average_transaction_amount,
    ROUND(
        100.0 * AVG(
            CASE
                WHEN transaction_status = 'approved' THEN 1
                ELSE 0
            END
        ),
        2
    ) AS approval_rate_pct
FROM transactions
GROUP BY 1
ORDER BY 1;

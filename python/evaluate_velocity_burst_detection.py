from pathlib import Path

import duckdb
import pandas as pd

DB_PATH = "finops.duckdb"
OUTPUT_PATH = Path("data/generated/velocity_burst_evaluation.csv")


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


QUERY = """
WITH ordered_transactions AS (
    SELECT
        transaction_id,
        employee_id,
        transaction_timestamp,
        amount,
        is_fraud,
        fraud_type,
        LAG(transaction_timestamp) OVER (
            PARTITION BY employee_id
            ORDER BY transaction_timestamp
        ) AS previous_transaction_timestamp
    FROM transactions
    WHERE transaction_status = 'approved'
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

scored_transactions AS (
    SELECT
        bg.transaction_id,
        bg.employee_id,
        bg.transaction_timestamp,
        bg.amount,
        bg.is_fraud,
        bg.fraud_type,
        bs.transactions_in_burst,
        CASE
            WHEN bs.transactions_in_burst >= 3 THEN 1
            ELSE 0
        END AS predicted_velocity_fraud
    FROM burst_groups AS bg
    JOIN burst_sizes AS bs
        ON bg.employee_id = bs.employee_id
        AND bg.burst_id = bs.burst_id
)

SELECT *
FROM scored_transactions;
"""


def main() -> None:
    conn = duckdb.connect(DB_PATH)
    df = conn.execute(QUERY).df()
    conn.close()

    velocity_fraud = df["fraud_type"] == "velocity_attack"
    predicted = df["predicted_velocity_fraud"] == 1

    true_positive = int((velocity_fraud & predicted).sum())
    false_positive = int((~velocity_fraud & predicted).sum())
    false_negative = int((velocity_fraud & ~predicted).sum())
    true_negative = int((~velocity_fraud & ~predicted).sum())

    precision = safe_divide(true_positive, true_positive + false_positive)
    recall = safe_divide(true_positive, true_positive + false_negative)
    false_positive_rate = safe_divide(
        false_positive,
        false_positive + true_negative,
    )

    summary = pd.DataFrame(
        [
            {
                "method": "burst_level_3_transactions_10_minutes",
                "true_positive": true_positive,
                "false_positive": false_positive,
                "false_negative": false_negative,
                "true_negative": true_negative,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "false_positive_rate": round(false_positive_rate, 4),
                "alerts_generated": int(predicted.sum()),
            }
        ]
    )

    summary.to_csv(OUTPUT_PATH, index=False)

    print("\nBurst-Level Velocity Detection Evaluation")
    print("=" * 75)
    print(summary.to_string(index=False))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

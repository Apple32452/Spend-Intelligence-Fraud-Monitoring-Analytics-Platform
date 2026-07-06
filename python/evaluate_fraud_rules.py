from pathlib import Path

import duckdb
import pandas as pd

DB_PATH = "finops.duckdb"
OUTPUT_DIR = Path("data/generated")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCORING_QUERY = """
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
        transaction_id,
        employee_id,
        transaction_timestamp,
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

transaction_features AS (
    SELECT
        t.transaction_id,
        t.company_id,
        t.employee_id,
        t.transaction_timestamp,
        t.amount,
        t.is_international,
        t.is_fraud,
        t.fraud_type,
        ets.employee_avg_amount,
        ets.employee_amount_stddev,
        bs.transactions_in_burst
    FROM transactions AS t
    JOIN employee_transaction_stats AS ets
        ON t.employee_id = ets.employee_id
    JOIN burst_groups AS bg
        ON t.transaction_id = bg.transaction_id
    JOIN burst_sizes AS bs
        ON bg.employee_id = bs.employee_id
        AND bg.burst_id = bs.burst_id
    WHERE t.transaction_status = 'approved'
),

scored_transactions AS (
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
    *,
    large_transaction_flag
        + unusual_amount_flag
        + velocity_flag
        + international_risk_flag AS fraud_risk_score,
    CASE
        WHEN large_transaction_flag
           + unusual_amount_flag
           + velocity_flag
           + international_risk_flag >= 1
        THEN 1
        ELSE 0
    END AS predicted_fraud
FROM scored_transactions
"""

def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def main() -> None:
    conn = duckdb.connect(DB_PATH)
    scored = conn.execute(SCORING_QUERY).df()
    conn.close()

    scored["is_fraud"] = scored["is_fraud"].astype(int)
    scored["predicted_fraud"] = scored["predicted_fraud"].astype(int)

    true_positive = int(
        ((scored["is_fraud"] == 1) & (scored["predicted_fraud"] == 1)).sum()
    )
    false_positive = int(
        ((scored["is_fraud"] == 0) & (scored["predicted_fraud"] == 1)).sum()
    )
    true_negative = int(
        ((scored["is_fraud"] == 0) & (scored["predicted_fraud"] == 0)).sum()
    )
    false_negative = int(
        ((scored["is_fraud"] == 1) & (scored["predicted_fraud"] == 0)).sum()
    )

    precision = safe_divide(true_positive, true_positive + false_positive)
    recall = safe_divide(true_positive, true_positive + false_negative)
    false_positive_rate = safe_divide(
        false_positive,
        false_positive + true_negative,
    )

    fraud_dollars = scored.loc[
        scored["is_fraud"] == 1,
        "amount",
    ].sum()

    captured_fraud_dollars = scored.loc[
        (scored["is_fraud"] == 1)
        & (scored["predicted_fraud"] == 1),
        "amount",
    ].sum()

    summary = pd.DataFrame(
        [
            {
                "approved_transactions_scored": len(scored),
                "ground_truth_fraud_transactions": int(scored["is_fraud"].sum()),
                "alerts_generated": int(scored["predicted_fraud"].sum()),
                "true_positive": true_positive,
                "false_positive": false_positive,
                "true_negative": true_negative,
                "false_negative": false_negative,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "false_positive_rate": round(false_positive_rate, 4),
                "alert_rate": round(scored["predicted_fraud"].mean(), 4),
                "fraud_dollars": round(float(fraud_dollars), 2),
                "fraud_dollars_captured": round(
                    float(captured_fraud_dollars),
                    2,
                ),
                "fraud_dollar_capture_rate": round(
                    safe_divide(
                        float(captured_fraud_dollars),
                        float(fraud_dollars),
                    ),
                    4,
                ),
            }
        ]
    )

    by_type = (
        scored[scored["fraud_type"] != "none"]
        .groupby("fraud_type")
        .agg(
            fraud_transactions=("is_fraud", "sum"),
            detected_transactions=("predicted_fraud", "sum"),
            average_amount=("amount", "mean"),
            fraud_dollars=("amount", "sum"),
        )
        .reset_index()
    )

    by_type["recall"] = (
        by_type["detected_transactions"]
        / by_type["fraud_transactions"]
    ).round(4)

    summary.to_csv(
        OUTPUT_DIR / "fraud_rule_evaluation_summary.csv",
        index=False,
    )

    by_type.to_csv(
        OUTPUT_DIR / "fraud_rule_evaluation_by_type.csv",
        index=False,
    )

    scored.to_csv(
        OUTPUT_DIR / "fraud_rule_scored_transactions.csv",
        index=False,
    )

    print("\nFraud Rule Evaluation")
    print("=" * 60)
    print(summary.to_string(index=False))

    print("\nPerformance by Fraud Type")
    print("=" * 60)
    print(by_type.to_string(index=False))

    print("\nSaved:")
    print("  data/generated/fraud_rule_evaluation_summary.csv")
    print("  data/generated/fraud_rule_evaluation_by_type.csv")
    print("  data/generated/fraud_rule_scored_transactions.csv")


if __name__ == "__main__":
    main()

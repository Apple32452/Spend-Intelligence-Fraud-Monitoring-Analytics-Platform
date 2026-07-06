from pathlib import Path

import duckdb
import pandas as pd

DB_PATH = "finops.duckdb"
OUTPUT_PATH = Path("data/generated/velocity_threshold_experiment.csv")

EXPERIMENTS = [
    {"window_minutes": 10, "minimum_transactions": 3},
    {"window_minutes": 10, "minimum_transactions": 4},
    {"window_minutes": 10, "minimum_transactions": 5},
    {"window_minutes": 15, "minimum_transactions": 3},
    {"window_minutes": 15, "minimum_transactions": 4},
    {"window_minutes": 20, "minimum_transactions": 4},
]


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def run_experiment(
    conn: duckdb.DuckDBPyConnection,
    window_minutes: int,
    minimum_transactions: int,
) -> dict:
    query = f"""
    WITH transaction_velocity AS (
        SELECT
            transaction_id,
            employee_id,
            transaction_timestamp,
            is_fraud,
            fraud_type,
            COUNT(*) OVER (
                PARTITION BY employee_id
                ORDER BY transaction_timestamp
                RANGE BETWEEN INTERVAL {window_minutes} MINUTE PRECEDING
                      AND CURRENT ROW
            ) AS transactions_in_window
        FROM transactions
        WHERE transaction_status = 'approved'
    ),

    scored AS (
        SELECT
            *,
            CASE
                WHEN transactions_in_window >= {minimum_transactions}
                THEN 1
                ELSE 0
            END AS predicted_velocity_fraud
        FROM transaction_velocity
    )

    SELECT
        SUM(
            CASE
                WHEN fraud_type = 'velocity_attack'
                 AND predicted_velocity_fraud = 1
                THEN 1
                ELSE 0
            END
        ) AS true_positive,

        SUM(
            CASE
                WHEN fraud_type != 'velocity_attack'
                 AND predicted_velocity_fraud = 1
                THEN 1
                ELSE 0
            END
        ) AS false_positive,

        SUM(
            CASE
                WHEN fraud_type = 'velocity_attack'
                 AND predicted_velocity_fraud = 0
                THEN 1
                ELSE 0
            END
        ) AS false_negative,

        SUM(
            CASE
                WHEN fraud_type != 'velocity_attack'
                 AND predicted_velocity_fraud = 0
                THEN 1
                ELSE 0
            END
        ) AS true_negative,

        SUM(predicted_velocity_fraud) AS total_alerts
    FROM scored;
    """

    row = conn.execute(query).fetchone()

    true_positive, false_positive, false_negative, true_negative, total_alerts = [
        int(value or 0) for value in row
    ]

    return {
        "window_minutes": window_minutes,
        "minimum_transactions": minimum_transactions,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "total_alerts": total_alerts,
        "precision": round(
            safe_divide(true_positive, true_positive + false_positive),
            4,
        ),
        "recall": round(
            safe_divide(true_positive, true_positive + false_negative),
            4,
        ),
        "false_positive_rate": round(
            safe_divide(false_positive, false_positive + true_negative),
            4,
        ),
    }


def main() -> None:
    conn = duckdb.connect(DB_PATH)

    results = [
        run_experiment(
            conn,
            experiment["window_minutes"],
            experiment["minimum_transactions"],
        )
        for experiment in EXPERIMENTS
    ]

    conn.close()

    results_df = pd.DataFrame(results).sort_values(
        ["recall", "precision"],
        ascending=False,
    )

    results_df.to_csv(OUTPUT_PATH, index=False)

    print("\nVelocity Rule Threshold Experiment")
    print("=" * 90)
    print(results_df.to_string(index=False))

    best_row = results_df.iloc[0]

    print("\nHighest-recall configuration:")
    print(
        f"{int(best_row['minimum_transactions'])} transactions "
        f"within {int(best_row['window_minutes'])} minutes"
    )
    print(f"Recall: {best_row['recall']:.2%}")
    print(f"Precision: {best_row['precision']:.2%}")
    print(f"False-positive rate: {best_row['false_positive_rate']:.2%}")

    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

from pathlib import Path

import duckdb

DB_PATH = "finops.duckdb"
SQL_DIR = Path("sql")
OUTPUT_DIR = Path("data/generated")

QUERY_OUTPUTS = {
    "01_spend_overview.sql": "monthly_spend_overview.csv",
    "02_budget_risk.sql": "budget_risk_alerts.csv",
    "03_fraud_rules.sql": "fraud_alerts.csv",
    "04_merchant_declines.sql": "merchant_decline_analysis.csv",
}


def main() -> None:
    conn = duckdb.connect(DB_PATH)

    for sql_file, output_file in QUERY_OUTPUTS.items():
        query_path = SQL_DIR / sql_file
        output_path = OUTPUT_DIR / output_file

        query = query_path.read_text()
        df = conn.execute(query).df()
        df.to_csv(output_path, index=False)

        print(
            f"Completed {sql_file}: "
            f"{len(df):,} rows -> {output_path}"
        )

    conn.close()


if __name__ == "__main__":
    main()

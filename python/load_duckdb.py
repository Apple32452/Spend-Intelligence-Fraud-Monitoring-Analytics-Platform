from pathlib import Path

import duckdb

DATA_DIR = Path("data/generated")
DB_PATH = "finops.duckdb"


def main() -> None:
    conn = duckdb.connect(DB_PATH)

    for table_name in ["companies", "employees", "merchants", "transactions"]:
        csv_path = DATA_DIR / f"{table_name}.csv"

        conn.execute(f"DROP TABLE IF EXISTS {table_name}")

        conn.execute(
            f"""
            CREATE TABLE {table_name} AS
            SELECT *
            FROM read_csv_auto('{csv_path}')
            """
        )

        count = conn.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]

        print(f"Loaded {table_name}: {count:,} rows")

    conn.close()
    print(f"\nCreated database: {DB_PATH}")


if __name__ == "__main__":
    main()

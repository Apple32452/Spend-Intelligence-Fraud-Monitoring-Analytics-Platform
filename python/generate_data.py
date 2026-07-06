from pathlib import Path
from datetime import datetime, timedelta
import random

import numpy as np
import pandas as pd
from faker import Faker

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

fake = Faker()
Faker.seed(SEED)

OUTPUT_DIR = Path("data/generated")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

N_COMPANIES = 100
N_EMPLOYEES = 2_000
N_MERCHANTS = 300
N_TRANSACTIONS = 50_000

CATEGORIES = [
    "Software",
    "Travel",
    "Meals",
    "Office Supplies",
    "Advertising",
    "Cloud Infrastructure",
    "Professional Services",
    "Transportation",
]

MERCHANTS = [
    "Amazon",
    "Uber",
    "AWS",
    "Google Cloud",
    "Microsoft",
    "Delta",
    "United Airlines",
    "Hilton",
    "Marriott",
    "OpenAI",
    "Salesforce",
    "Slack",
    "Notion",
]


def generate_companies() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "company_id": range(1, N_COMPANIES + 1),
            "company_name": [fake.company() for _ in range(N_COMPANIES)],
            "industry": np.random.choice(
                ["Technology", "Finance", "Healthcare", "Retail", "Consulting"],
                N_COMPANIES,
            ),
            "created_at": [
                fake.date_between(start_date="-4y", end_date="-30d")
                for _ in range(N_COMPANIES)
            ],
        }
    )


def generate_employees(companies: pd.DataFrame) -> pd.DataFrame:
    company_ids = np.random.choice(companies["company_id"], N_EMPLOYEES)

    return pd.DataFrame(
        {
            "employee_id": range(1, N_EMPLOYEES + 1),
            "company_id": company_ids,
            "employee_name": [fake.name() for _ in range(N_EMPLOYEES)],
            "department": np.random.choice(
                ["Engineering", "Sales", "Marketing", "Finance", "Operations"],
                N_EMPLOYEES,
            ),
            "monthly_budget": np.random.randint(1000, 8000, N_EMPLOYEES),
        }
    )


def generate_merchants() -> pd.DataFrame:
    merchant_names = [
        random.choice(MERCHANTS) if i < len(MERCHANTS) else fake.company()
        for i in range(N_MERCHANTS)
    ]

    return pd.DataFrame(
        {
            "merchant_id": range(1, N_MERCHANTS + 1),
            "merchant_name": merchant_names,
            "category": np.random.choice(CATEGORIES, N_MERCHANTS),
            "country": np.random.choice(
                ["US", "CA", "GB", "DE", "JP"],
                N_MERCHANTS,
                p=[0.75, 0.08, 0.08, 0.05, 0.04],
            ),
        }
    )


def inject_large_amount_fraud(
    transactions: pd.DataFrame,
    rng: np.random.Generator,
    n_rows: int = 500,
) -> None:
    available_rows = transactions.index[transactions["is_fraud"] == 0]
    chosen_rows = rng.choice(available_rows, size=n_rows, replace=False)

    transactions.loc[chosen_rows, "amount"] = np.round(
        np.maximum(
            transactions.loc[chosen_rows, "amount"].to_numpy() * rng.uniform(
                18, 35, size=n_rows
            ),
            6000,
        ),
        2,
    )

    transactions.loc[chosen_rows, "transaction_status"] = "approved"
    transactions.loc[chosen_rows, "decline_reason"] = None
    transactions.loc[chosen_rows, "is_fraud"] = 1
    transactions.loc[chosen_rows, "fraud_type"] = "large_amount"


def inject_international_fraud(
    transactions: pd.DataFrame,
    rng: np.random.Generator,
    n_rows: int = 300,
) -> None:
    available_rows = transactions.index[transactions["is_fraud"] == 0]
    chosen_rows = rng.choice(available_rows, size=n_rows, replace=False)

    transactions.loc[chosen_rows, "amount"] = np.round(
        np.maximum(
            transactions.loc[chosen_rows, "amount"].to_numpy() * rng.uniform(
                8, 18, size=n_rows
            ),
            1200,
        ),
        2,
    )

    transactions.loc[chosen_rows, "merchant_country"] = rng.choice(
        ["CA", "GB", "DE", "JP"],
        size=n_rows,
    )
    transactions.loc[chosen_rows, "is_international"] = True
    transactions.loc[chosen_rows, "transaction_status"] = "approved"
    transactions.loc[chosen_rows, "decline_reason"] = None
    transactions.loc[chosen_rows, "is_fraud"] = 1
    transactions.loc[chosen_rows, "fraud_type"] = "international_purchase"


def inject_velocity_fraud(
    transactions: pd.DataFrame,
    rng: np.random.Generator,
    n_groups: int = 40,
) -> None:
    available = transactions[transactions["is_fraud"] == 0]

    eligible_employees = (
        available.groupby("employee_id")
        .size()
        .loc[lambda x: x >= 4]
        .index
        .to_numpy()
    )

    chosen_employees = rng.choice(
        eligible_employees,
        size=n_groups,
        replace=False,
    )

    start_date = datetime.now() - timedelta(days=365)

    for employee_id in chosen_employees:
        employee_rows = transactions.index[
            (transactions["employee_id"] == employee_id)
            & (transactions["is_fraud"] == 0)
        ]

        chosen_rows = rng.choice(employee_rows, size=4, replace=False)

        anchor_time = start_date + timedelta(
            days=int(rng.integers(0, 360)),
            minutes=int(rng.integers(0, 24 * 60)),
        )

        for offset_minutes, row_index in zip([0, 2, 4, 7], chosen_rows):
            transactions.loc[
                row_index,
                "transaction_timestamp",
            ] = anchor_time + timedelta(minutes=offset_minutes)

            transactions.loc[row_index, "amount"] = round(
                max(
                    float(transactions.loc[row_index, "amount"]),
                    float(rng.uniform(1000, 3000)),
                ),
                2,
            )

            transactions.loc[row_index, "transaction_status"] = "approved"
            transactions.loc[row_index, "decline_reason"] = None
            transactions.loc[row_index, "is_fraud"] = 1
            transactions.loc[row_index, "fraud_type"] = "velocity_attack"


def generate_transactions(
    employees: pd.DataFrame,
    merchants: pd.DataFrame,
) -> pd.DataFrame:
    employee_sample = employees.sample(
        N_TRANSACTIONS,
        replace=True,
    ).reset_index(drop=True)

    merchant_sample = merchants.sample(
        N_TRANSACTIONS,
        replace=True,
    ).reset_index(drop=True)

    start_date = datetime.now() - timedelta(days=365)

    timestamps = [
        start_date + timedelta(minutes=random.randint(0, 365 * 24 * 60))
        for _ in range(N_TRANSACTIONS)
    ]

    amounts = np.round(
        np.random.lognormal(mean=4.2, sigma=1.0, size=N_TRANSACTIONS),
        2,
    )

    statuses = np.random.choice(
        ["approved", "declined"],
        N_TRANSACTIONS,
        p=[0.92, 0.08],
    )

    transactions = pd.DataFrame(
        {
            "transaction_id": range(1, N_TRANSACTIONS + 1),
            "company_id": employee_sample["company_id"],
            "employee_id": employee_sample["employee_id"],
            "merchant_id": merchant_sample["merchant_id"],
            "transaction_timestamp": timestamps,
            "amount": amounts,
            "transaction_status": statuses,
            "decline_reason": np.where(
                statuses == "declined",
                np.random.choice(
                    [
                        "insufficient_funds",
                        "suspected_fraud",
                        "merchant_blocked",
                        "card_expired",
                    ],
                    N_TRANSACTIONS,
                ),
                None,
            ),
            "is_international": merchant_sample["country"].ne("US"),
            "merchant_country": merchant_sample["country"],
            "is_fraud": 0,
            "fraud_type": "none",
        }
    )

    rng = np.random.default_rng(SEED)

    inject_large_amount_fraud(transactions, rng)
    inject_international_fraud(transactions, rng)
    inject_velocity_fraud(transactions, rng)

    return transactions


def main() -> None:
    companies = generate_companies()
    employees = generate_employees(companies)
    merchants = generate_merchants()
    transactions = generate_transactions(employees, merchants)

    companies.to_csv(OUTPUT_DIR / "companies.csv", index=False)
    employees.to_csv(OUTPUT_DIR / "employees.csv", index=False)
    merchants.to_csv(OUTPUT_DIR / "merchants.csv", index=False)
    transactions.to_csv(OUTPUT_DIR / "transactions.csv", index=False)

    fraud_count = int(transactions["is_fraud"].sum())

    print("Generated:")
    print(f"  companies: {len(companies):,}")
    print(f"  employees: {len(employees):,}")
    print(f"  merchants: {len(merchants):,}")
    print(f"  transactions: {len(transactions):,}")
    print(f"  labeled fraud transactions: {fraud_count:,}")
    print("\nFraud labels:")
    print(
        transactions["fraud_type"]
        .value_counts()
        .to_string()
    )


if __name__ == "__main__":
    main()

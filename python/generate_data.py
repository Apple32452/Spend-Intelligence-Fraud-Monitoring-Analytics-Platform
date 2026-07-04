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


def generate_transactions(
    employees: pd.DataFrame, merchants: pd.DataFrame
) -> pd.DataFrame:
    employee_sample = employees.sample(
        N_TRANSACTIONS, replace=True
    ).reset_index(drop=True)

    merchant_sample = merchants.sample(
        N_TRANSACTIONS, replace=True
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
        }
    )

    suspicious_rows = transactions.sample(
        frac=0.01,
        random_state=SEED,
    ).index

    transactions.loc[suspicious_rows, "amount"] *= 20
    transactions.loc[suspicious_rows, "transaction_status"] = "approved"

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

    print("Generated:")
    print(f"  companies: {len(companies):,}")
    print(f"  employees: {len(employees):,}")
    print(f"  merchants: {len(merchants):,}")
    print(f"  transactions: {len(transactions):,}")


if __name__ == "__main__":
    main()

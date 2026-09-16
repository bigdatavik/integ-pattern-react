"""Generate sample data for demo purposes."""

import csv
import io
import json
import random
from datetime import datetime, timedelta


FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "David", "Elizabeth", "William", "Barbara", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Christopher", "Karen",
    "Charles", "Lisa", "Daniel", "Nancy", "Matthew", "Betty", "Anthony",
    "Margaret", "Mark", "Sandra", "Steven", "Ashley", "Paul", "Dorothy",
    "Andrew", "Kimberly", "Joshua", "Emily", "Kenneth", "Donna",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
]

CITIES = [
    ("New York", "NY"), ("Los Angeles", "CA"), ("Chicago", "IL"),
    ("Houston", "TX"), ("Phoenix", "AZ"), ("Philadelphia", "PA"),
    ("San Antonio", "TX"), ("San Diego", "CA"), ("Dallas", "TX"),
    ("San Jose", "CA"), ("Austin", "TX"), ("Jacksonville", "FL"),
    ("Columbus", "OH"), ("Charlotte", "NC"), ("Indianapolis", "IN"),
    ("Seattle", "WA"), ("Denver", "CO"), ("Nashville", "TN"),
    ("Portland", "OR"), ("Atlanta", "GA"),
]


def _random_date(start_year: int = 2020, end_year: int = 2025) -> str:
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = (end - start).days
    d = start + timedelta(days=random.randint(0, delta))
    return d.strftime("%Y-%m-%d")


def generate_customer_records(n: int = 30) -> list:
    """Generate n sample customer records."""
    records = []
    for i in range(1, n + 1):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        city, state = random.choice(CITIES)
        created = _random_date(2020, 2024)
        updated = _random_date(2024, 2025)
        records.append({
            "customer_id": f"CUST-{i:05d}",
            "customer_name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}{i}@example.com",
            "city": city,
            "state": state,
            "created_date": created,
            "updated_date": updated,
        })
    return records


def generate_order_records(n: int = 30) -> list:
    """Generate n sample order records (for Oracle pattern)."""
    statuses = ["PENDING", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"]
    records = []
    for i in range(1, n + 1):
        records.append({
            "order_id": f"ORD-{i:06d}",
            "customer_id": f"CUST-{random.randint(1, 20):05d}",
            "order_date": _random_date(2024, 2025),
            "order_amount": round(random.uniform(10.0, 2500.0), 2),
            "status": random.choice(statuses),
            "source_system": "ORACLE_ERP",
            "updated_date": _random_date(2025, 2025),
        })
    return records


def records_to_csv(records: list) -> str:
    """Convert records to CSV string."""
    if not records:
        return ""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=records[0].keys())
    writer.writeheader()
    writer.writerows(records)
    return output.getvalue()


def records_to_json(records: list) -> str:
    """Convert records to JSON string."""
    return json.dumps(records, indent=2)

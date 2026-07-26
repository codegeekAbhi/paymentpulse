"""
db.py
SQLite storage layer and synthetic payment failure data for PaymentPulse.
"""
import sqlite3
import threading
import uuid
import random
from datetime import datetime, timedelta, timezone

from faker import Faker

fake = Faker()
random.seed(42)

DB_PATH = "paymentpulse.db"
CONFIDENCE_THRESHOLD = 0.85  # below this, route to human review
DB_LOCK = threading.Lock()  # sqlite connections are not safe to share across threads without one

FAILURE_CODES = {
    "insufficient_funds": "Card declined due to insufficient funds",
    "card_expired": "Card has expired",
    "cvv_mismatch": "CVV verification failed",
    "fraud_suspected": "Transaction flagged by fraud detection",
    "processor_timeout": "Payment processor timed out",
    "invalid_account": "Bank account details invalid",
    "currency_mismatch": "Currency not supported for this account",
    "limit_exceeded": "Transaction exceeds daily limit",
}


PAYMENT_METHODS = ["credit_card", "debit_card", "ach", "wallet", "bank_transfer"]


CUSTOMER_TIERS = ["free", "standard", "premium", "enterprise"]


def generate_transaction():
    failure_code, failure_message = random.choice(list(FAILURE_CODES.items()))
    return {
        "transaction_id": str(uuid.uuid4())[:8],
        "amount": round(random.uniform(5, 2500), 2),
        "currency": random.choice(["USD", "EUR", "GBP", "INR"]),
        "payment_method": random.choice(PAYMENT_METHODS),
        "merchant": fake.company(),
        "customer_tier": random.choice(CUSTOMER_TIERS),
        "failure_code": failure_code,
        "failure_message": failure_message,
        "raw_gateway_response": f"{failure_code.upper()}: {failure_message}. Ref {fake.bothify('??######')}",
        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=random.randint(0, 10000))).isoformat(),
    }


def init_db(path=DB_PATH):
    # check_same_thread=False lets the FastAPI background thread reuse this
    # connection; DB_LOCK (used below) is what actually keeps writes safe.
    conn = sqlite3.connect(path, check_same_thread=False)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            amount REAL,
            currency TEXT,
            payment_method TEXT,
            merchant TEXT,
            customer_tier TEXT,
            failure_code TEXT,
            failure_message TEXT,
            raw_gateway_response TEXT,
            timestamp TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS classifications (
            transaction_id TEXT PRIMARY KEY,
            root_cause TEXT,
            confidence REAL,
            suggested_action TEXT,
            reasoning TEXT,
            classified_at TEXT,
            FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS routing_decisions (
            transaction_id TEXT PRIMARY KEY,
            route TEXT,
            resolved_by TEXT,
            final_action TEXT,
            resolved_at TEXT,
            FOREIGN KEY (transaction_id) REFERENCES transactions (transaction_id)
        )
    ''')
    conn.commit()
    return conn


def insert_transactions(conn, txns):
    with DB_LOCK:
        cur = conn.cursor()
        for t in txns:
            cur.execute('''
                INSERT OR REPLACE INTO transactions
                (transaction_id, amount, currency, payment_method, merchant, customer_tier,
                 failure_code, failure_message, raw_gateway_response, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (t["transaction_id"], t["amount"], t["currency"], t["payment_method"],
                  t["merchant"], t["customer_tier"], t["failure_code"], t["failure_message"],
                  t["raw_gateway_response"], t["timestamp"]))
        conn.commit()
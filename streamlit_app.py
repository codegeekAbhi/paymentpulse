import sqlite3
import uuid
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

DB_PATH = "paymentpulse.db"

st.set_page_config(page_title="PaymentPulse", layout="wide")
st.title("PaymentPulse: Payment Failure Intelligence")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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


conn = get_connection()

# amount, currency, payment_method, merchant, customer_tier, failure_code, failure_message,
# root_cause, confidence, suggested_action, reasoning
SAMPLE_TRANSACTIONS = [
    (129.99, "USD", "credit_card", "Acme Retail", "premium", "card_expired", "Card has expired",
     "Expired Card", 0.98, "Contact customer to update card on file",
     "Gateway response explicitly states the card has expired, leaving little ambiguity."),
    (89.50, "USD", "debit_card", "Northwind Traders", "standard", "insufficient_funds",
     "Card declined due to insufficient funds", "Insufficient Funds", 0.95,
     "Retry payment in 48 hours or notify customer",
     "Standard decline code with a clear match to the failure message."),
    (450.00, "EUR", "wallet", "Globex Corp", "enterprise", "fraud_suspected",
     "Transaction flagged by fraud detection", "Possible Fraud", 0.62,
     "Escalate to fraud review team",
     "Fraud flags require manual confirmation since automated signals can be false positives."),
    (1200.00, "GBP", "bank_transfer", "Initech", "enterprise", "processor_timeout",
     "Payment processor timed out", "Unclear: Processor Timeout", 0.41,
     "Manual review required, retry outcome uncertain",
     "Timeouts can stem from the gateway, the bank, or network issues, root cause is not clear from this data alone."),
    (65.20, "USD", "ach", "Umbrella Corp", "free", "invalid_account",
     "Bank account details invalid", "Invalid Account Details", 0.91,
     "Contact customer to verify account number",
     "Account validation failures are usually straightforward data entry issues."),
    (310.75, "INR", "credit_card", "Wayne Enterprises", "premium", "currency_mismatch",
     "Currency not supported for this account", "Currency Mismatch", 0.88,
     "Offer alternate currency or payment method",
     "Clear mismatch between the transaction currency and the account's supported currencies."),
    (2499.00, "USD", "credit_card", "Stark Industries", "enterprise", "limit_exceeded",
     "Transaction exceeds daily limit", "Daily Limit Exceeded", 0.93,
     "Suggest splitting payment or retry next day",
     "Limit failures are deterministic and rarely require judgment calls."),
    (75.00, "USD", "wallet", "Oscorp", "standard", "cvv_mismatch", "CVV verification failed",
     "CVV Mismatch", 0.55, "Ask customer to re-enter card details",
     "CVV failures can stem from either a typo or an attempted fraud, harder to distinguish from this data alone."),
]


def load_sample_data():
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.cursor()
    for row in SAMPLE_TRANSACTIONS:
        (amount, currency, payment_method, merchant, customer_tier, failure_code, failure_message,
         root_cause, confidence, suggested_action, reasoning) = row
        tid = str(uuid.uuid4())[:8]
        cur.execute('''
            INSERT OR REPLACE INTO transactions
            (transaction_id, amount, currency, payment_method, merchant, customer_tier,
             failure_code, failure_message, raw_gateway_response, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tid, amount, currency, payment_method, merchant, customer_tier,
              failure_code, failure_message, f"{failure_code.upper()}: {failure_message}", now))
        cur.execute('''
            INSERT OR REPLACE INTO classifications
            (transaction_id, root_cause, confidence, suggested_action, reasoning, classified_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (tid, root_cause, confidence, suggested_action, reasoning, now))
        route = "auto_resolve" if confidence >= 0.85 else "human_review"
        cur.execute('''
            INSERT OR REPLACE INTO routing_decisions
            (transaction_id, route, resolved_by, final_action, resolved_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (tid, route,
              "system" if route == "auto_resolve" else None,
              suggested_action if route == "auto_resolve" else None,
              now if route == "auto_resolve" else None))
    conn.commit()


with st.sidebar:
    st.header("Demo controls")
    if st.button("Load sample data"):
        load_sample_data()
        st.success("Sample transactions loaded.")
        st.rerun()

overview = pd.read_sql_query('''
    SELECT r.route, COUNT(*) as count
    FROM routing_decisions r
    GROUP BY r.route
''', conn)

col1, col2, col3 = st.columns(3)
total = int(overview["count"].sum()) if not overview.empty else 0
auto = int(overview.loc[overview["route"] == "auto_resolve", "count"].sum()) if not overview.empty else 0
human = int(overview.loc[overview["route"] == "human_review", "count"].sum()) if not overview.empty else 0

col1.metric("Total routed", total)
col2.metric("Auto resolved", auto)
col3.metric("Sent to human review", human)

if total == 0:
    st.info(
        "No transactions yet. Use 'Load sample data' in the sidebar to see the dashboard "
        "populated, or point this app at a paymentpulse.db file produced by the live pipeline."
    )

st.subheader("Human review queue")
queue = pd.read_sql_query('''
    SELECT t.transaction_id, t.merchant, t.amount, t.currency, t.customer_tier,
           c.root_cause, c.confidence, c.suggested_action
    FROM routing_decisions r
    JOIN transactions t ON t.transaction_id = r.transaction_id
    JOIN classifications c ON c.transaction_id = r.transaction_id
    WHERE r.route = 'human_review'
''', conn)
st.dataframe(queue, use_container_width=True)

st.subheader("All classifications")
all_classified = pd.read_sql_query('''
    SELECT t.transaction_id, t.merchant, t.failure_code, c.root_cause, c.confidence, c.suggested_action
    FROM transactions t
    JOIN classifications c ON c.transaction_id = t.transaction_id
    ORDER BY c.confidence DESC
''', conn)
st.dataframe(all_classified, use_container_width=True)

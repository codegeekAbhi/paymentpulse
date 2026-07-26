import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "paymentpulse.db"

st.set_page_config(page_title="PaymentPulse", layout="wide")
st.title("PaymentPulse: Payment Failure Intelligence")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)

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
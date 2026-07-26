"""
main.py
Generates sample data, classifies it, routes it, and prints the results.
Run the API separately with: uvicorn api:app --reload
"""
from db import init_db, insert_transactions, generate_transaction
from classifier import classify_and_store
from routing import route_all, get_review_queue

if __name__ == "__main__":
    conn = init_db()
    transactions = [generate_transaction() for _ in range(50)]
    insert_transactions(conn, transactions)
    classify_and_store(conn, transactions[:10])
    routes = route_all(conn)
    print(routes)
    print(get_review_queue(conn))


# ---------------------------------------------------------------
# Reference: extra cells from the notebook that were not part of
# db, classifier, routing, or api (test calls, scratch exploration).
# Not wired into the flow above, kept here for reference only.
# ---------------------------------------------------------------

# import sqlite3
# import json
# import random
# import time
# import uuid
# import threading
# from datetime import datetime, timedelta, timezone
# 
# import pandas as pd
# from faker import Faker
# 
# fake = Faker()
# random.seed(42)
# 
# DB_PATH = "paymentpulse.db"
# CONFIDENCE_THRESHOLD = 0.85  # below this, route to human review
# DB_LOCK = threading.Lock()  # sqlite connections are not safe to share across threads without one

# ambiguous_txn = {
#     "transaction_id": str(uuid.uuid4())[:8],
#     "amount": 340.00,
#     "currency": "USD",
#     "payment_method": "credit_card",
#     "merchant": "Test Merchant",
#     "customer_tier": "standard",
#     "failure_code": "processor_timeout",
#     "failure_message": "Payment processor timed out",
#     "raw_gateway_response": "UNKNOWN_ERROR: connection reset, no further details available",
#     "timestamp": datetime.now(timezone.utc).isoformat(),
# }
# 
# # 1. store the transaction
# insert_transactions(conn, [ambiguous_txn])
# 
# # 2. classify it
# result = classify_transaction(ambiguous_txn)
# print(result)
# 
# # 3. store the classification
# with DB_LOCK:
#     cur = conn.cursor()
#     cur.execute('''
#         INSERT OR REPLACE INTO classifications
#         (transaction_id, root_cause, confidence, suggested_action, reasoning, classified_at)
#         VALUES (?, ?, ?, ?, ?, ?)
#     ''', (ambiguous_txn["transaction_id"], result.get("root_cause"), result.get("confidence"),
#           result.get("suggested_action"), result.get("reasoning"), datetime.now(timezone.utc).isoformat()))
#     conn.commit()
# 
# # 4. route it
# route = route_transaction(conn, ambiguous_txn["transaction_id"])
# print("Route:", route)
# 
# # 5. check the queue
# get_review_queue(conn)

# from google.colab.output import eval_js
# 
# proxy_url = eval_js("google.colab.kernel.proxyPort(8000)")
# docs_url = proxy_url.rstrip("/") + "/docs"
# print("Open this in your browser:", docs_url)

# #Test the API
# 
# import requests
# time.sleep(2)
# test_payload = {
#     "amount": 129.99,
#     "currency": "USD",
#     "payment_method": "credit_card",
#     "merchant": "Acme Retail",
#     "customer_tier": "premium",
#     "failure_code": "card_expired",
#     "failure_message": "Card has expired",
#     "raw_gateway_response": "CARD_EXPIRED: Card has expired. Ref AB123456",
# }
# response = requests.post("http://127.0.0.1:8000/classify", json=test_payload)
# response.json()

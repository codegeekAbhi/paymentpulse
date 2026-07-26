"""
routing.py
Confidence threshold routing and the human in the loop review queue.
"""
from datetime import datetime, timezone

import pandas as pd

from db import DB_LOCK, CONFIDENCE_THRESHOLD

def route_transaction(conn, transaction_id, threshold=CONFIDENCE_THRESHOLD):
    with DB_LOCK:
        cur = conn.cursor()
        cur.execute("SELECT confidence, suggested_action FROM classifications WHERE transaction_id = ?", (transaction_id,))
        row = cur.fetchone()
        if row is None:
            return None
        confidence, suggested_action = row
        route = "auto_resolve" if confidence >= threshold else "human_review"
        cur.execute('''
            INSERT OR REPLACE INTO routing_decisions
            (transaction_id, route, resolved_by, final_action, resolved_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            transaction_id,
            route,
            "system" if route == "auto_resolve" else None,
            suggested_action if route == "auto_resolve" else None,
            datetime.now(timezone.utc).isoformat() if route == "auto_resolve" else None,
        ))
        conn.commit()
    return route


def route_all(conn, threshold=CONFIDENCE_THRESHOLD):
    cur = conn.cursor()
    cur.execute("SELECT transaction_id FROM classifications")
    ids = [r[0] for r in cur.fetchall()]
    routes = {tid: route_transaction(conn, tid, threshold) for tid in ids}
    return routes


def get_review_queue(conn):
    query = '''
        SELECT t.transaction_id, t.merchant, t.amount, t.currency, t.customer_tier,
               c.root_cause, c.confidence, c.suggested_action
        FROM routing_decisions r
        JOIN transactions t ON t.transaction_id = r.transaction_id
        JOIN classifications c ON c.transaction_id = r.transaction_id
        WHERE r.route = 'human_review'
    '''
    return pd.read_sql_query(query, conn)


def resolve_review(conn, transaction_id, resolved_by, final_action):
    with DB_LOCK:
        cur = conn.cursor()
        cur.execute('''
            UPDATE routing_decisions
            SET resolved_by = ?, final_action = ?, resolved_at = ?
            WHERE transaction_id = ?
        ''', (resolved_by, final_action, datetime.now(timezone.utc).isoformat(), transaction_id))
        conn.commit()
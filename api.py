"""
api.py
FastAPI service layer wrapping the pipeline.
Run directly with: uvicorn api:app --reload
"""
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from db import DB_LOCK, init_db, insert_transactions
from classifier import classify_transaction
from routing import route_transaction, get_review_queue, resolve_review

app = FastAPI(title="PaymentPulse API")
conn = init_db()

class TransactionIn(BaseModel):
    amount: float
    currency: str
    payment_method: str
    merchant: str
    customer_tier: str
    failure_code: str
    failure_message: str
    raw_gateway_response: str


class ResolveIn(BaseModel):
    resolved_by: str
    final_action: str


@app.post("/classify")
def api_classify(txn: TransactionIn):
    payload = txn.model_dump()
    payload["transaction_id"] = str(uuid.uuid4())[:8]
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    insert_transactions(conn, [payload])
    result = classify_transaction(payload)
    with DB_LOCK:
        cur = conn.cursor()
        cur.execute('''
            INSERT OR REPLACE INTO classifications
            (transaction_id, root_cause, confidence, suggested_action, reasoning, classified_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (payload["transaction_id"], result.get("root_cause"), result.get("confidence"),
              result.get("suggested_action"), result.get("reasoning"), datetime.now(timezone.utc).isoformat()))
        conn.commit()
    route = route_transaction(conn, payload["transaction_id"])
    return {"transaction_id": payload["transaction_id"], "classification": result, "route": route}


@app.get("/review-queue")
def api_review_queue():
    return get_review_queue(conn).to_dict(orient="records")


@app.post("/review-queue/{transaction_id}/resolve")
def api_resolve(transaction_id: str, body: ResolveIn):
    resolve_review(conn, transaction_id, body.resolved_by, body.final_action)
    return {"status": "resolved", "transaction_id": transaction_id}


@app.get("/transactions/{transaction_id}")
def api_get_transaction(transaction_id: str):
    df = pd.read_sql_query(
        "SELECT * FROM transactions WHERE transaction_id = ?", conn, params=(transaction_id,)
    )
    if df.empty:
        raise HTTPException(status_code=404, detail="transaction not found")
    return df.to_dict(orient="records")[0]


def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

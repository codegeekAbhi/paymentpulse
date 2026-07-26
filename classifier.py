"""
classifier.py
LLM based failure classification using Groq and Llama.
"""
import os
import json
import time
from datetime import datetime, timezone

from groq import Groq

from db import DB_LOCK

GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or input("Enter your Groq API key: ")
client = Groq(api_key=GROQ_API_KEY)

MODEL = "llama-3.3-70b-versatile"


CLASSIFICATION_PROMPT = '''You are a payment operations analyst. Given the transaction and the raw gateway response below, identify the true root cause of the failure, how confident you are, and the best next action.

Transaction:
- Amount: {amount} {currency}
- Payment method: {payment_method}
- Customer tier: {customer_tier}
- Gateway failure code: {failure_code}
- Raw gateway response: {raw_gateway_response}

Respond with ONLY a JSON object, no extra text, in this exact shape:
{{
  "root_cause": "short label for the underlying issue",
  "confidence": 0.0 to 1.0,
  "suggested_action": "one clear next step, such as retry payment, contact customer, escalate to fraud team, or update card on file",
  "reasoning": "one or two sentences explaining the call"
}}
'''


def classify_transaction(txn: dict) -> dict:
    prompt = CLASSIFICATION_PROMPT.format(**txn)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=300,
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "root_cause": "unclassified",
            "confidence": 0.0,
            "suggested_action": "manual review required, model output was not valid JSON",
            "reasoning": raw[:200],
        }
    return result


def classify_and_store(conn, txns, delay=0.3):
    for t in txns:
        result = classify_transaction(t)
        with DB_LOCK:
            cur = conn.cursor()
            cur.execute('''
                INSERT OR REPLACE INTO classifications
                (transaction_id, root_cause, confidence, suggested_action, reasoning, classified_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (t["transaction_id"], result.get("root_cause"), result.get("confidence"),
                  result.get("suggested_action"), result.get("reasoning"), datetime.now(timezone.utc).isoformat()))
            conn.commit()
        time.sleep(delay)  # be gentle on rate limits
    print(f"Classified {len(txns)} transactions")
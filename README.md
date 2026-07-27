# PaymentPulse

AI powered payment failure intelligence platform. Classifies failed transactions using Llama 3.3 70b via Groq, scores its own confidence, and routes uncertain cases to a human review queue instead of guessing.

`python` `fastapi` `sqlite` `streamlit` `supabase` `llm` `groq` `llama` `payments` `fintech` `human-in-the-loop` `ai-agents`

## Live demos

- **Streamlit dashboard**, reads from the Python and SQLite pipeline: https://paymentpulse.streamlit.app/
- **Lovable app**, interactive live classifier, backed by Postgres via Lovable Cloud: https://paymentpulse-insight-hub.lovable.app

## Overview

Payment failures come back from gateways as terse, inconsistent error codes. PaymentPulse takes that raw failure data, asks Llama 3.3 70b (through Groq) to identify the actual root cause and the best next action, and only auto resolves the cases the model is confident about. Everything below a configurable confidence threshold gets queued for a human to review instead of being guessed at.

This repo contains two working implementations of that same idea:

1. A Python pipeline (FastAPI plus SQLite) with a Streamlit dashboard, the original build.
2. A Lovable built web app (React frontend, Postgres via Lovable Cloud) with a live, interactive classifier anyone can test directly in the browser.

Both run the same core logic underneath: classify, score confidence, route.

---

## 1. Python pipeline and Streamlit dashboard

### How it works

1. **Data layer** (`db.py`): synthetic payment failure events and a SQLite schema with three tables, transactions, classifications, and routing_decisions.
2. **Classification** (`classifier.py`): sends each transaction's gateway response to Llama 3.3 70b through the Groq API, gets back a structured root cause, a confidence score, a suggested action, and a short explanation.
3. **Routing** (`routing.py`): transactions at or above the confidence threshold are auto resolved. Everything else goes to a human review queue.
4. **API** (`api.py`): a FastAPI service exposing the pipeline over HTTP.
5. **Dashboard** (`streamlit_app.py`): a Streamlit view of routing outcomes and the review queue.

### Project structure
paymentpulse/
├── db.py # SQLite schema, synthetic data generation
├── classifier.py # Groq and Llama classification logic
├── routing.py # Confidence threshold routing, review queue
├── api.py # FastAPI service layer
├── main.py # End to end demo script
├── streamlit_app.py # Streamlit dashboard
├── requirements.txt
└── README.md

### Setup

Requires Python 3.10 or newer.

```bash
pip install -r requirements.txt
```

Set your Groq API key as an environment variable (get one at console.groq.com):

```bash
export GROQ_API_KEY=your_key_here
```

If it is not set, the scripts will prompt for it on first run.

### Running it

**Batch demo**, generates sample data, classifies it, and prints routing results:

```bash
python main.py
```

**API server**:

```bash
uvicorn api:app --reload
```

Then visit `http://127.0.0.1:8000/docs` for the interactive Swagger UI.

**Dashboard**:

```bash
pip install streamlit pandas
streamlit run streamlit_app.py
```

Opens at `http://localhost:8501` by default. Run the main pipeline at least once first, `python main.py` or a few calls to `/classify`, so `paymentpulse.db` has data in it, the dashboard reads that file directly and does not generate or classify data on its own. It also has its own "Load Sample Data" button for a quick populated view without running the rest of the pipeline first.

If you are running the rest of the pipeline in Google Colab, Streamlit will not render inline in a notebook cell, run it in a separate terminal instead, or tunnel it out with pyngrok.

### API endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/classify` | Submit a transaction, get back its root cause, confidence, suggested action, and routing decision |
| GET | `/review-queue` | List transactions currently routed to human review |
| POST | `/review-queue/{transaction_id}/resolve` | Mark a queued transaction as resolved, with who resolved it and the final action taken |
| GET | `/transactions/{transaction_id}` | Look up a single transaction's stored details |

---

## 2. Lovable app

A more polished, interactive rebuild of the same concept, live at the link above.

### What it does

- Everything the Streamlit dashboard shows, total routed, auto resolved versus human review breakdown, a full human review queue, and a searchable, sortable table of every classification
- **Try It Yourself**: paste any payment failure scenario, real or made up, merchant, failure code, and raw gateway response, and watch Llama 3.3 70b classify it live, with the actual confidence score, reasoning, and routing decision, not a canned example
- **Load Sample Data**: seeds a realistic batch of demo transactions with a single click, safe to run repeatedly
- **Resolve flow**: close out queued items with a resolved by and final action, written back live to the database

### Stack

React, Postgres (managed via Lovable Cloud), Groq (Llama 3.3 70b).

### Notes

This implementation is fully hosted, there is no local setup, just open the live link above. It runs on its own managed backend separate from the Python pipeline's SQLite file, the two implementations do not share data with each other, each is a complete, independent demonstration of the same underlying idea.

---

## Confidence threshold routing

The default threshold is 0.85 across both implementations. Anything the model scores at or above that is auto resolved and logged as such. Anything below it, or anything the model returns as unparseable output, is routed to human_review instead.

## Roadmap

- Multi-agent recovery pipeline: a second agent drafting the actual customer facing recovery action, a third agent detecting systemic patterns across transactions rather than judging them one at a time
- Trend tracking, human and model agreement rate tracking, and an audit trail of every routing decision
- A dollar impact panel estimating manual review hours saved at the current threshold

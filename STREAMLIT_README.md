# PaymentPulse Dashboard

A Streamlit view of routing outcomes and the human review queue, reading directly from the same SQLite database the main pipeline writes to.

## Prerequisites

Run the main pipeline at least once first, either `python main.py` or a few calls to the `/classify` endpoint, so `paymentpulse.db` has data in it. The dashboard reads that file directly, it does not generate or classify data on its own.

## Running locally

```bash
pip install streamlit pandas
streamlit run streamlit_app.py
```

Opens at `http://localhost:8501` by default.

## What it shows

- Total transactions routed, split between auto resolved and sent to human review
- The full human review queue, with root cause, confidence, and suggested action for each item
- All classifications across every transaction, sorted by confidence

## Notes

- The dashboard opens its own SQLite connection separate from the API's, both point at the same `paymentpulse.db` file, so run it alongside the API rather than instead of it if you want live data.
- If you are running the rest of the pipeline in Google Colab, Streamlit will not render inline in a notebook cell. Run this file in a separate terminal, or tunnel it out of Colab with pyngrok.

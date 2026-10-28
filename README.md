# AI-Powered Chatbot for University Student Support

Local project prototype combining an intent classifier, FAQ retrieval, sentiment signal, escalation policy, Flask API, and Streamlit chat UI.

## Run locally

1. Create and activate a Python virtual environment.
2. Install dependencies: `python -m pip install -r requirements.txt`.
3. Train the baseline intent model: `python -m src.intent --train`.
4. Start the local API in one terminal: `python -m api.app`.
5. Start the chat UI in another terminal: `streamlit run ui/streamlit_app.py`.
6. Open the local Streamlit URL shown in the terminal.

The API binds to `127.0.0.1` by default. Keep it local: the demo ticket queue has no authentication. The first FAQ search may download the MiniLM sentence-embedding model.

## Project data and demo mode

The API uses `data/faq_real_data.csv` by default (`CHATBOT_FAQ_PATH` can point to another CSV). It only serves rows marked `verified=true` with an official HTTP(S) source. The current file has 16 eligible rows out of 36; unverified rows are kept in the CSV but are not used as answers. Set `FAQ_DEMO_MODE=true` only to preview unverified content. The older `data/faq.csv` remains available as the project sample dataset.

The demo includes no live ERP/LMS integration. Sensitive intents always escalate. Escalated tickets store a PII-masked transcript in `data/tickets.sqlite3`; conversation state and repeat-question hashes are held in memory. Feedback is stored without message text.

## API routes

- `GET /health`
- `POST /chat` with `{ "session_id": "...", "message": "..." }`
- `POST /escalate` with an optional `opt_out: true`
- `POST /feedback` with `rating` from 1 to 5
- `GET /tickets?limit=100` (local prototype only; unauthenticated)

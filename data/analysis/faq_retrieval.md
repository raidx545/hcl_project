# FAQ retrieval component

Implemented in `src/retriever.py` with a sentence-transformers MiniLM encoder and cosine similarity. The encoder and index are created only when at least one eligible FAQ exists.

## Safety and matching behavior

- Only rows marked `verified=true` with a non-empty answer and an HTTP(S) source URL enter the searchable index.
- The default similarity threshold is 0.45 as an initial configuration value. It has not been tuned against a verified FAQ evaluation set.
- Retrieval first searches within the predicted intent. A global fallback can suggest candidates, but it does not automatically return an answer from a different intent; that case returns `best_faq_intent_mismatch` and requires escalation.
- `grievance`, harassment, mental-health, and payment-dispute intents are blocked from direct FAQ answers and marked for human escalation.
- No eligible FAQ match returns `answer=null` with `escalate=true`.
- Candidates expose question, source, and score for routing/debugging, not answer content. Only a successful verified match includes an answer.

All current `data/faq.csv` entries are project sample data with `verified=false` and blank source URLs. The retriever defaults to production-safe filtering, while the local Flask prototype enables explicit demo mode so you can exercise answers from these rows. The Streamlit UI labels them as illustrative sample content. Turn demo mode off to require verified rows and official source URLs. For any deployment beyond this personal prototype, replace sample answers with official information and tune the threshold on a labeled validation query set.

## Use

From the repository root:

```sh
python3 -m src.retriever --query "How do I request a fee installment plan?" --intent fees
```

The CLI prints a JSON result. Sensitive or unmatched queries set `escalate=true`.

# Sentiment and escalation components

Implemented in `src/sentiment.py`, `src/escalation.py`, and `src/session.py`.

## Sentiment

The sentiment analyzer uses VADER when the `vaderSentiment` package is installed. A small built-in word-list fallback allows development without that dependency, but it is not validated and should not be reported as model performance. The dataset has no sentiment labels; `user_rating` is not substituted for message sentiment. Sentiment is only one escalation signal.

## Escalation rules

A handoff is required for an opt-out, explicit human request (including selected Hinglish phrases), sensitive intent/topic, out-of-scope/anomaly flag, strongly negative sentiment (compound score <= -0.50), missing/low intent confidence (< 0.60), absent/unmatched FAQ, low FAQ score (< 0.45), or a question repeated at least twice after its first occurrence. Defaults are initial policy values from the project report and still need validation with staff.

Sensitive intents include grievance, harassment, mental health, and payment dispute. Sensitive topics are also detected by a conservative keyword pattern. This is a simple safeguard, not a complete crisis or safety classifier; configure verified institutional contacts and human routing before any real use.

The function returns a machine-readable decision with reasons and a student-facing handoff message. It does not persist message content. `SessionManager` holds only query hashes in memory and can clear session state on opt-out or close. It must remain process-local and should not be backed by persistent storage for this purpose.

## Use

```python
from src.escalation import EscalationEngine

engine = EscalationEngine()
decision = engine.evaluate(
    query='I have asked twice already, please connect me to a person',
    intent='fees', confidence=0.55, faq_match=False,
)
```

When integrating, call the retriever first, pass its `matched` and score into the engine, and show an answer only when `decision['escalate']` is false and the retriever returned a verified answer.

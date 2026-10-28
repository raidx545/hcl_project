# FAQ knowledge base

`faq.csv` contains 36 mock/demo question-answer entries aligned to the six intents in `dataset.csv`: fees, exams, hostel, admissions, library, and grievance.

## Before using these answers

The dataset contains student questions but no authoritative answers. The answer text in `faq.csv` is invented mock/demo content for development only; it is not university policy. Every entry remains `verified=false`, and `source_url` is blank. Do not present these answers as real guidance. Before any real use, replace them with information checked against current official university sources, add those source URLs, and set `verified=true` only for entries that were actually checked.

For grievance and safety topics, configure the chatbot to escalate directly to a human. The sample text is not an emergency service; add verified institutional reporting and emergency contacts before any real deployment. Do not make the bot the sole responder to harassment, ragging, or other sensitive concerns.

## CSV fields

- `faq_id`: stable identifier for an FAQ entry.
- `intent`: one of the dataset's six intent labels.
- `question`: canonical question to embed for retrieval; add paraphrases as separate rows or a dedicated aliases field if your retriever supports it.
- `answer`: answer shown to the student after verification.
- `source_url`: official university source supporting the answer.
- `verified`: `false` until the answer has been checked against its source.

Filter out rows where `verified` is not `true`, `answer` is empty, or `source_url` is not an official HTTP(S) source at runtime. The retriever in `src/retriever.py` enforces these checks. Keep this file UTF-8 encoded.

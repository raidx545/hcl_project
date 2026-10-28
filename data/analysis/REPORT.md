# Dataset EDA and preprocessing notes

Generated from the 5,000-row `dataset.csv`; raw data was not modified. Charts and CSV tables are in this folder.

## Main observations

- The most frequent intent is **exams** (1,115 rows); the least frequent is **grievance** (503). See `intent_distribution.csv` and `figures/intent_distribution.png`.
- Escalation rate is highest for **grievance** (58.1%) and lowest for **fees** (9.4%). These are observed historical labels, not policy targets.
- Ratings: 1: 151, 2: 258, 3: 805, 4: 1,891, 5: 1,895. See `rating_distribution.csv`.
- Original logged confidence averages 0.872 for non-escalated rows and 0.704 for escalated rows. Treat this column as descriptive only; do not use it as a model feature because it was produced by the prior system.
- Query length: median 138 characters; range 68–187 characters.
- Timestamps span 2026-07-01 through 2026-10-09. See daily, weekday, and hour count tables and charts.
- 172 rows are flagged as anomalies across 4 anomaly/fault types. Their intent labels are ordinary helpdesk intents, and there is no `out_of_scope` label. Keep these out of normal intent training until reviewed; construct a separately reviewed OOD evaluation set.
- There are 929 repeated normalized-query groups, with 5 groups that have conflicting intent labels. The split script keeps every repeated query in one partition, but conflicting labels still need manual review.
- Heuristic PII scan found 0 email-like and 0 phone-like query strings. This pattern scan is not proof that all PII is absent; the data contains redaction markers, and a dedicated scrubber should be applied before any persistent logs.

## Preprocessing decisions for modeling

1. Preserve the raw source file. Apply transformations in the model pipeline or to generated copies only.
2. Normalize text with Unicode normalization, case-folding, and whitespace trimming. Mask URLs, email addresses, phone numbers, and student/roll numbers before storage and model input.
3. Do not remove stopwords aggressively; short queries may depend on them. Do not include `confidence_score`, `escalated`, `user_rating`, `resolution_status`, `timestamp`, `session_id`, or `is_anomaly` as intent-model features.
4. Use the grouped split files under `data/splits/`. Tune preprocessing and thresholds on train/validation only; use test once for final metrics.
5. Review the five mixed-label duplicate groups and all anomaly examples. Add a dedicated `out_of_scope` class only after deciding and validating labels; do not infer it from anomalous wording alone.
6. The FAQ file is mock content and must not be used for student-facing answers until its answers are replaced with sourced university information.

## Figures

- Intent counts: `figures/intent_distribution.png`
- Escalation by intent: `figures/escalation_by_intent.png`
- Ratings: `figures/rating_distribution.png`
- Confidence by escalation: `figures/confidence_by_escalation.png`
- Query lengths: `figures/query_length_distribution.png`
- Queries per day: `figures/queries_per_day.png`
- Queries by weekday: `figures/queries_by_weekday.png`

# Dataset preparation summary

- Source: `dataset.csv` (5,000 rows).
- Grouping: case-folded, whitespace-normalized `paraphrased_query`; all identical query text stays in one partition.
- Seed: 42; approximate target proportions among non-anomaly rows: 70% / 10% / 20%.
- Anomaly rows are excluded from standard intent-classifier splits because they are labeled with ordinary intents and there is no `out_of_scope` intent. They are preserved in `anomaly_holdout.csv` for separate OOD/safety evaluation.
- Repeated query groups in the full source: 929; groups with conflicting intent labels: 5.
- Mixed-label duplicate query groups remain intact in one split; inspect these labels before training.

| Partition | Rows | Intent counts |
|---|---:|---|
| `train.csv` | 3,378 | admissions: 696, exams: 747, fees: 663, grievance: 344, hostel: 463, library: 465 |
| `validation.csv` | 484 | admissions: 100, exams: 107, fees: 95, grievance: 49, hostel: 66, library: 67 |
| `test.csv` | 966 | admissions: 199, exams: 214, fees: 190, grievance: 98, hostel: 132, library: 133 |
| `anomaly_holdout.csv` | 172 | admissions: 30, exams: 47, fees: 38, grievance: 12, hostel: 21, library: 24 |

Before training, decide how to represent out-of-scope examples and review the conflicting-label groups. The anomaly holdout is not a substitute for a clean, human-reviewed OOD test set.

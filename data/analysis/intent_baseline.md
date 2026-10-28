# Intent classifier baseline

Implemented in `src/intent.py` and `src/preprocessing.py` using TF-IDF unigrams/bigrams with sublinear term frequency and balanced Logistic Regression. The pipeline applies Unicode normalization, case-folding, whitespace normalization, and basic masking for email, URL, phone, and student/roll-number patterns.

## Validation result

Trained on 3,378 non-anomaly rows and evaluated on 484 validation rows. **Accuracy: 1.000; macro F1: 1.000; weighted F1: 1.000.** Per-class metrics and the confusion matrix are in `intent_validation_per_class.csv` and `intent_validation_confusion_matrix.csv`.

The held-out test split was not read or evaluated. The saved model is `../../models/intent_tfidf_logreg.joblib` relative to this report.

## Important interpretation

The validation result is a perfect score, but it should be treated as preliminary. Exact normalized query strings were kept in one split, yet nearest-train TF-IDF cosine similarity is high: median 0.866, and 97.7% of validation messages have a training message at similarity >= 0.80. The dataset’s templated, topic-specific wording may make this task much easier than real student traffic. Before claiming performance, create a harder evaluation split grouped by underlying question/template family and evaluate real, independently written messages. Do not tune or report final results from the test set until the model choice and thresholds are fixed.

The classifier has only six in-scope classes. It has no `out_of_scope` class and the maximum class probability is not calibrated; route low-confidence or sensitive topics through explicit safety/escalation rules rather than treating this model as an OOD detector.

## Reproduce

From the project root, install `requirements.txt` and run:

```sh
python3 -m src.intent --train
```

This trains from `data/splits/train.csv`, evaluates only `data/splits/validation.csv`, and writes the model and validation outputs. `data/splits/test.csv` remains untouched.

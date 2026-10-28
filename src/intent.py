"""TF-IDF + Logistic Regression baseline for university support intents.

Train/tune only on the prepared train and validation partitions. The test split is
intentionally not read by this script.
"""
import argparse
import csv
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import Pipeline

from src.preprocessing import TextNormalizer

ROOT = Path(__file__).resolve().parents[1]
TRAIN = ROOT / 'data' / 'splits' / 'train.csv'
VALIDATION = ROOT / 'data' / 'splits' / 'validation.csv'
MODEL_PATH = ROOT / 'models' / 'intent_tfidf_logreg.joblib'
RESULTS_DIR = ROOT / 'data' / 'analysis'
EXPECTED_INTENTS = {'admissions', 'exams', 'fees', 'grievance', 'hostel', 'library'}


def read_rows(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def build_model():
    return Pipeline([
        ('normalize', TextNormalizer()),
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True,
                                  strip_accents='unicode', min_df=1,
                                  max_features=100_000)),
        ('classifier', LogisticRegression(class_weight='balanced', max_iter=1000,
                                          random_state=42)),
    ])


def validate_rows(rows, label):
    if not rows:
        raise ValueError(f'{label} split is empty')
    if any(r.get('is_anomaly') == '1' for r in rows):
        raise ValueError(f'{label} split contains anomaly rows; regenerate splits first')
    found = {r['intent'] for r in rows}
    unexpected = found - EXPECTED_INTENTS
    if unexpected:
        raise ValueError(f'Unexpected intent labels in {label}: {sorted(unexpected)}')


def train():
    train_rows, val_rows = read_rows(TRAIN), read_rows(VALIDATION)
    validate_rows(train_rows, 'train')
    validate_rows(val_rows, 'validation')
    X_train = [r['paraphrased_query'] for r in train_rows]
    y_train = [r['intent'] for r in train_rows]
    X_val = [r['paraphrased_query'] for r in val_rows]
    y_val = [r['intent'] for r in val_rows]

    model = build_model()
    model.fit(X_train, y_train)
    pred = model.predict(X_val)
    proba = model.predict_proba(X_val)
    confidence = proba.max(axis=1)
    # Diagnose how close each validation example is to any training example.
    # High lexical similarity can make a random row split look overly optimistic.
    train_vectors = model[:-1].transform(X_train)
    validation_vectors = model[:-1].transform(X_val)
    nearest_train_similarity = cosine_similarity(
        validation_vectors, train_vectors, dense_output=True
    ).max(axis=1)
    labels = sorted(EXPECTED_INTENTS)
    report = classification_report(y_val, pred, labels=labels, output_dict=True,
                                   zero_division=0)
    metrics = {
        'model': 'TF-IDF (unigrams+bigrams, sublinear_tf) + LogisticRegression(class_weight=balanced)',
        'validation_rows': len(val_rows),
        'train_rows': len(train_rows),
        'accuracy': accuracy_score(y_val, pred),
        'macro_f1': f1_score(y_val, pred, labels=labels, average='macro', zero_division=0),
        'weighted_f1': f1_score(y_val, pred, labels=labels, average='weighted', zero_division=0),
        'mean_max_class_probability': float(confidence.mean()),
        'nearest_train_tfidf_cosine_similarity': {
            'median': float(np.median(nearest_train_similarity)),
            'p90': float(np.percentile(nearest_train_similarity, 90)),
            'share_at_least_0_80': float(np.mean(nearest_train_similarity >= 0.80)),
            'share_at_least_0_90': float(np.mean(nearest_train_similarity >= 0.90)),
        },
        'per_class': {label: report[label] for label in labels},
        'classes': labels,
        'test_split_used': False,
        'notes': [
            'Validation metrics are preliminary model-selection results, not final held-out performance.',
            'Near-duplicate families may still cross partitions even though exact normalized queries are grouped; inspect similarity diagnostics before interpreting validation scores.',
            'No out_of_scope class exists in the source labels; confidence alone is not calibrated and must not be treated as a safe OOD detector.',
            'No user_query_type, confidence_score, escalated, user_rating, timestamp, session_id, resolution_status, or is_anomaly field was used as a feature.'
        ]
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    (RESULTS_DIR / 'intent_validation_metrics.json').write_text(
        json.dumps(metrics, indent=2), encoding='utf-8')

    cm = confusion_matrix(y_val, pred, labels=labels)
    with (RESULTS_DIR / 'intent_validation_confusion_matrix.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['true_intent\\predicted_intent', *labels])
        for label, row in zip(labels, cm):
            writer.writerow([label, *row.tolist()])
    with (RESULTS_DIR / 'intent_validation_per_class.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['intent','precision','recall','f1-score','support'])
        for label in labels:
            m = report[label]
            writer.writerow([label, m['precision'], m['recall'], m['f1-score'], int(m['support'])])
    with (RESULTS_DIR / 'intent_validation_predictions.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['session_id','true_intent','predicted_intent','max_class_probability','correct'])
        for row, true, guess, score in zip(val_rows, y_val, pred, confidence):
            writer.writerow([row['session_id'], true, guess, round(float(score), 6), str(true == guess).lower()])
    print(f"Model saved: {MODEL_PATH}")
    print(f"Validation: accuracy={metrics['accuracy']:.4f}, macro_f1={metrics['macro_f1']:.4f}, weighted_f1={metrics['weighted_f1']:.4f}")
    print(f"Validation details: {RESULTS_DIR / 'intent_validation_metrics.json'}")
    print('Held-out test split was not read.')


def predict(path):
    model = joblib.load(MODEL_PATH)
    rows = read_rows(Path(path))
    texts = [r['paraphrased_query'] for r in rows]
    preds = model.predict(texts)
    probs = model.predict_proba(texts).max(axis=1)
    writer = csv.writer(__import__('sys').stdout)
    writer.writerow(['predicted_intent','max_class_probability'])
    for label, prob in zip(preds, probs):
        writer.writerow([label, f'{prob:.6f}'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--train', action='store_true', help='fit on train.csv and report validation metrics')
    group.add_argument('--predict', metavar='CSV', help='predict for a CSV containing paraphrased_query')
    args = parser.parse_args()
    if args.train:
        train()
    else:
        predict(args.predict)

if __name__ == '__main__':
    main()

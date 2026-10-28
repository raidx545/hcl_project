"""Grounded FAQ retrieval with verified-answer filtering and intent safeguards."""
import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
from sentence_transformers import SentenceTransformer

from src.preprocessing import normalize_text

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FAQ_PATH = ROOT / 'data' / 'faq.csv'
DEFAULT_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
DEFAULT_THRESHOLD = 0.45
SENSITIVE_INTENTS = {'grievance', 'harassment', 'mental_health', 'payment_dispute'}


def _is_http_url(value):
    parsed = urlparse((value or '').strip())
    return parsed.scheme in {'https', 'http'} and bool(parsed.netloc)


def _is_verified(value):
    return (value or '').strip().casefold() in {'true', '1', 'yes'}


class FAQRetriever:
    """Retrieve only sourced, verified FAQ answers using cosine similarity.

    The encoder and vectors are initialized lazily. Unverified/mock rows are removed
    before embedding, and the answer is exposed only for a confident intent match.
    """

    def __init__(self, faq_path=DEFAULT_FAQ_PATH, model_name=DEFAULT_MODEL,
                 threshold=DEFAULT_THRESHOLD, sensitive_intents=None,
                 demo_mode=False):
        if not 0 <= threshold <= 1:
            raise ValueError('threshold must be between 0 and 1')
        self.faq_path = Path(faq_path)
        self.model_name = model_name
        self.threshold = threshold
        self.demo_mode = demo_mode
        self.sensitive_intents = set(sensitive_intents or SENSITIVE_INTENTS)
        self.entries = self._load_verified_entries()
        self._model = None
        self._embeddings = None

    def _load_verified_entries(self):
        with self.faq_path.open(newline='', encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
        needed = {'faq_id', 'intent', 'question', 'answer', 'source_url', 'verified'}
        if rows and not needed.issubset(rows[0]):
            raise ValueError(f'FAQ CSV missing fields: {sorted(needed - set(rows[0]))}')
        return [
            {
                'faq_id': row['faq_id'].strip(),
                'intent': row['intent'].strip().casefold(),
                'question': row['question'].strip(),
                'answer': row['answer'].strip(),
                'source_url': row['source_url'].strip(),
            }
            for row in rows
            if (
                (self.demo_mode or (_is_verified(row.get('verified'))
                                    and _is_http_url(row.get('source_url'))))
                and row.get('question', '').strip()
                and row.get('answer', '').strip()
            )
        ]

    def _ensure_index(self):
        if not self.entries or self._embeddings is not None:
            return
        self._model = SentenceTransformer(self.model_name)
        questions = [normalize_text(item['question']) for item in self.entries]
        self._embeddings = self._model.encode(
            questions, convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)

    def retrieve(self, query, intent=None, top_k=3):
        """Return answer only for an eligible, above-threshold FAQ of same intent.

        A global search is used as a diagnostic fallback when intent filtering has
        no confident result. A result from another intent is never automatically
        returned as the answer.
        """
        query = normalize_text(query)
        intent = (intent or '').strip().casefold() or None
        if not query:
            return self._no_match('empty_query')
        if intent in self.sensitive_intents:
            return {
                'matched': False,
                'answer': None,
                'reason': 'sensitive_intent_requires_human',
                'escalate': True,
                'candidates': [],
            }
        if not self.entries:
            return self._no_match('no_verified_faqs')
        if top_k < 1:
            raise ValueError('top_k must be at least 1')

        self._ensure_index()
        query_vector = self._model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False,
        )[0].astype(np.float32)
        scores = self._embeddings @ query_vector

        scoped = [i for i, entry in enumerate(self.entries)
                  if intent is None or entry['intent'] == intent]
        scoped_ranked = sorted(scoped, key=lambda i: float(scores[i]), reverse=True)
        scoped_best = scoped_ranked[0] if scoped_ranked else None
        if scoped_best is not None and float(scores[scoped_best]) >= self.threshold:
            return self._matched(scoped_best, scores, scoped_ranked, top_k, 'intent')

        global_ranked = sorted(range(len(self.entries)), key=lambda i: float(scores[i]), reverse=True)
        if global_ranked and float(scores[global_ranked[0]]) >= self.threshold:
            best = global_ranked[0]
            if intent and self.entries[best]['intent'] != intent:
                return {
                    'matched': False,
                    'answer': None,
                    'reason': 'best_faq_intent_mismatch',
                    'escalate': True,
                    'candidates': self._candidate_list(global_ranked[:top_k], scores),
                }
            return self._matched(best, scores, global_ranked, top_k, 'global')

        return {
            'matched': False,
            'answer': None,
            'reason': 'similarity_below_threshold',
            'escalate': True,
            'candidates': self._candidate_list(global_ranked[:top_k], scores),
        }

    def _candidate_list(self, indices, scores):
        return [
            {
                'faq_id': self.entries[i]['faq_id'],
                'intent': self.entries[i]['intent'],
                'question': self.entries[i]['question'],
                'score': float(scores[i]),
                'source_url': self.entries[i]['source_url'],
            'source_label': ('Project demo FAQ (sample data)' if self.demo_mode
                             else self.entries[i]['source_url']),
            }
            for i in indices
        ]

    def _matched(self, best, scores, ranked, top_k, search_scope):
        entry = self.entries[best]
        return {
            'matched': True,
            'answer': entry['answer'],
            'faq_id': entry['faq_id'],
            'intent': entry['intent'],
            'score': float(scores[best]),
            'source_url': entry['source_url'],
            'source_label': ('Project demo FAQ (sample data)' if self.demo_mode
                             else entry['source_url']),
            'search_scope': search_scope,
            'reason': 'verified_faq_match',
            'escalate': False,
            'candidates': self._candidate_list(ranked[:top_k], scores),
        }

    @staticmethod
    def _no_match(reason):
        return {
            'matched': False,
            'answer': None,
            'reason': reason,
            'escalate': True,
            'candidates': [],
        }


def main():
    parser = argparse.ArgumentParser(description='Search verified FAQs only.')
    parser.add_argument('--query', required=True)
    parser.add_argument('--intent', default=None)
    parser.add_argument('--faq', type=Path, default=DEFAULT_FAQ_PATH)
    parser.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument('--demo-mode', action='store_true',
                        help='allow project sample answers even when not verified')
    args = parser.parse_args()
    result = FAQRetriever(args.faq, threshold=args.threshold,
                          demo_mode=args.demo_mode).retrieve(args.query, args.intent)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

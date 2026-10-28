"""Text normalization and lightweight PII masking for model input."""
import re
import unicodedata

from sklearn.base import BaseEstimator, TransformerMixin

_EMAIL = re.compile(r'(?i)\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b')
_URL = re.compile(r'(?i)\b(?:https?://|www\.)\S+')
# Common India phone formats; require 10 digits (optionally +91/91/0 prefix).
_PHONE = re.compile(r'(?<!\w)(?:(?:\+?91|0)[\s-]?)?[6-9]\d{9}(?!\w)')
_ROLL_LABEL = re.compile(r'(?i)\b(?:roll\s*(?:no\.?|number|#)|student\s*id)\s*[:#-]?\s*[A-Z0-9/-]{3,}\b')
_REDACTED = re.compile(r'\[(?:REDACTED_[A-Z_]+)\]', re.I)


def normalize_text(value):
    text = unicodedata.normalize('NFKC', str(value or '')).casefold()
    text = _EMAIL.sub(' pii_email ', text)
    text = _URL.sub(' pii_url ', text)
    text = _PHONE.sub(' pii_phone ', text)
    text = _ROLL_LABEL.sub(' pii_student_id ', text)
    text = _REDACTED.sub(' pii_redacted ', text)
    return ' '.join(text.split())


class TextNormalizer(BaseEstimator, TransformerMixin):
    """Sklearn-compatible normalizer that also masks common PII patterns."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return [normalize_text(value) for value in X]

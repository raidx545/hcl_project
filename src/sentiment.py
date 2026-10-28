"""Sentiment signal for escalation; not a standalone sentiment classifier."""
import re

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:  # Development fallback; install requirements for VADER.
    SentimentIntensityAnalyzer = None


_NEGATIVE = {
    'angry': 1.8, 'awful': 2.0, 'bad': 1.4, 'broken': 1.2, 'cancel': 0.7,
    'disappointed': 1.8, 'frustrated': 2.0, 'hate': 2.0, 'helpless': 1.8,
    'horrible': 2.2, 'ignored': 1.7, 'issue': 0.6, 'late': 0.5,
    'never': 0.9, 'nobody helps': 2.0, 'problem': 0.9, 'ridiculous': 2.0,
    'stupid': 1.8, 'terrible': 2.2, 'unfair': 1.7, 'useless': 2.0,
    'worst': 2.0, 'wrong': 0.8, ' परेशान': 1.2,
}
_POSITIVE = {
    'amazing': 2.0, 'awesome': 2.0, 'excellent': 2.0, 'good': 1.2,
    'great': 1.5, 'happy': 1.5, 'helpful': 1.3, 'love': 1.7,
    'perfect': 1.8, 'please': 0.2, 'resolved': 1.2, 'thanks': 0.8,
    'thank you': 1.0, 'wonderful': 2.0,
}
_NEGATORS = {'not', "n't", 'never', 'no', 'cannot', "can't", 'dont', "don't", 'isnt', "isn't"}
_INTENSIFIERS = {'very': 1.4, 'extremely': 1.8, 'really': 1.3, 'so': 1.2, 'too': 1.2}
_WORD_RE = re.compile(r"[\w']+", re.UNICODE)


class SentimentAnalyzer:
    """Use VADER when installed; otherwise use a small documented lexicon fallback."""

    def __init__(self):
        self._vader = SentimentIntensityAnalyzer() if SentimentIntensityAnalyzer else None

    @property
    def engine(self):
        return 'vader' if self._vader else 'development_lexicon_fallback'

    def analyze(self, text):
        text = str(text or '').strip()
        if not text:
            return {'label': 'neutral', 'score': 0.0, 'engine': self.engine}
        if self._vader:
            score = float(self._vader.polarity_scores(text)['compound'])
        else:
            score = self._fallback_score(text)
        label = 'negative' if score <= -0.05 else ('positive' if score >= 0.05 else 'neutral')
        return {'label': label, 'score': score, 'engine': self.engine}

    @staticmethod
    def _fallback_score(text):
        lower = text.casefold()
        tokens = _WORD_RE.findall(lower)
        token_set = set(tokens)
        neg = sum(weight for phrase, weight in _NEGATIVE.items() if phrase in lower)
        pos = sum(weight for phrase, weight in _POSITIVE.items() if phrase in lower)
        # A preceding negator reverses a nearby sentiment word approximately.
        if token_set & _NEGATORS:
            neg, pos = pos, neg
        boost = 1.0 + min(0.6, 0.2 * sum(t in _INTENSIFIERS for t in tokens))
        raw = (pos - neg) * boost
        if '!' in text:
            raw *= 1.15
        # Smoothly bound to [-1, 1]. This fallback is intentionally simple.
        return max(-1.0, min(1.0, raw / (1.0 + abs(raw))))


def analyze_sentiment(text):
    return SentimentAnalyzer().analyze(text)

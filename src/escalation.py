"""Transparent escalation policy for the student-support assistant."""
import re

from src.sentiment import SentimentAnalyzer

SENSITIVE_INTENTS = {'grievance', 'harassment', 'mental_health', 'payment_dispute'}
HUMAN_REQUESTS = (
    'talk to a human', 'speak to a human', 'connect me to a human',
    'human agent', 'real person', 'speak to a person', 'talk to an agent',
    'kisi insaan se baat karao', 'kisi insaan se baat karni hai',
    'mujhe human se baat karni hai', 'advisor se baat',
)
SENSITIVE_QUERY = re.compile(
    r'(?i)\b(harassment|ragging|sexual misconduct|stalk(?:ing)?|'
    r'suicid(?:e|al)|self[- ]harm|mental health crisis|'
    r'payment dispute|charged twice|unauthori[sz]ed (?:charge|payment)|'
    r'money deducted but (?:payment )?failed|fraudulent payment)\b'
)


class EscalationEngine:
    def __init__(self, confidence_threshold=0.60, retrieval_threshold=0.45,
                 sentiment_threshold=-0.50, sensitive_intents=None):
        for name, value in [('confidence_threshold', confidence_threshold),
                            ('retrieval_threshold', retrieval_threshold)]:
            if not 0 <= value <= 1:
                raise ValueError(f'{name} must be between 0 and 1')
        if not -1 <= sentiment_threshold <= 1:
            raise ValueError('sentiment_threshold must be between -1 and 1')
        self.confidence_threshold = confidence_threshold
        self.retrieval_threshold = retrieval_threshold
        self.sentiment_threshold = sentiment_threshold
        self.sensitive_intents = set(sensitive_intents or SENSITIVE_INTENTS)
        self.sentiment = SentimentAnalyzer()

    def evaluate(self, *, query='', intent=None, confidence=None,
                 retrieval_score=None, faq_match=None, repeat_count=0,
                 opt_out=False, explicit_human=None, sentiment_score=None,
                 anomaly=False):
        """Return whether to hand off, with stable machine-readable reasons.

        `repeat_count` is the number of times this normalized question has been
        repeated after its first occurrence (2 means third occurrence overall).
        `faq_match` must be true to permit a bot answer; false or unknown is safe-fail.
        """
        norm_intent = (intent or '').strip().casefold()
        sentiment = self.sentiment.analyze(query)
        score = sentiment['score'] if sentiment_score is None else float(sentiment_score)
        if not -1 <= score <= 1:
            raise ValueError('sentiment_score must be between -1 and 1')
        lower_query = str(query or '').casefold()
        wants_human = explicit_human if explicit_human is not None else any(
            phrase in lower_query for phrase in HUMAN_REQUESTS
        )
        reasons = []

        # Always-enforced routes come first; keep all applicable reasons for audit.
        if opt_out:
            reasons.append('opt_out_requested')
        if wants_human:
            reasons.append('explicit_human_request')
        if norm_intent in self.sensitive_intents or SENSITIVE_QUERY.search(lower_query):
            reasons.append('sensitive_topic')
        if anomaly or norm_intent in {'out_of_scope', 'anomaly', 'unknown'}:
            reasons.append('out_of_scope_or_anomaly')
        if score <= self.sentiment_threshold:
            reasons.append('strong_negative_sentiment')
        if confidence is None:
            reasons.append('intent_confidence_unavailable')
        elif float(confidence) < self.confidence_threshold:
            reasons.append('low_intent_confidence')
        if faq_match is False:
            reasons.append('no_verified_faq_match')
        elif faq_match is None and retrieval_score is None:
            reasons.append('faq_result_unavailable')
        if retrieval_score is not None and float(retrieval_score) < self.retrieval_threshold:
            reasons.append('low_faq_similarity')
        if int(repeat_count) >= 2:
            reasons.append('repeated_question')

        return {
            'escalate': bool(reasons),
            'reasons': reasons,
            'route': 'human' if reasons else 'faq_answer',
            'sentiment': {'label': sentiment['label'], 'score': score,
                          'engine': sentiment['engine']},
            'student_message': self._student_message(reasons),
        }

    @staticmethod
    def _student_message(reasons):
        if not reasons:
            return None
        if 'sensitive_topic' in reasons:
            return 'This topic needs support from a person. I’m connecting you to a human advisor.'
        if 'opt_out_requested' in reasons or 'explicit_human_request' in reasons:
            return 'I’m connecting you to a human advisor now.'
        return 'I’m not confident I can answer this safely, so I’m connecting you to a human advisor.'


def should_escalate(**kwargs):
    """Convenience wrapper returning the full policy decision."""
    return EscalationEngine().evaluate(**kwargs)

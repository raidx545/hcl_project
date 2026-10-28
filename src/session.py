"""In-memory, PII-minimizing session state for repeat-question detection."""
import hashlib
from collections import Counter, defaultdict

from src.preprocessing import normalize_text


class SessionManager:
    """Track normalized-query hashes only; call end_session to discard state."""

    def __init__(self):
        self._counts = defaultdict(Counter)
        self._opted_out = set()

    def record_query(self, session_id, query):
        if session_id in self._opted_out:
            return {'repeat_count': 0, 'opted_out': True}
        digest = hashlib.sha256(normalize_text(query).encode('utf-8')).hexdigest()
        prior_count = self._counts[session_id][digest]
        self._counts[session_id][digest] += 1
        return {'repeat_count': prior_count, 'opted_out': False}

    def opt_out(self, session_id):
        self._counts.pop(session_id, None)
        self._opted_out.add(session_id)
        return {'opted_out': True, 'route': 'human'}

    def end_session(self, session_id):
        self._counts.pop(session_id, None)
        self._opted_out.discard(session_id)

    def clear_history(self, session_id, preserve_opt_out=False):
        self._counts.pop(session_id, None)
        if not preserve_opt_out:
            self._opted_out.discard(session_id)

    def clear(self):
        self._counts.clear()
        self._opted_out.clear()

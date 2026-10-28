"""SQLite ticket and feedback store for the local project prototype."""
import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from src.preprocessing import normalize_text


class TicketStore:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self):
        with closing(self._connect()) as conn:
            with conn:
                conn.execute('''CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    intent TEXT,
                    reason TEXT NOT NULL,
                    sentiment TEXT,
                    transcript_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open'
                )''')
                conn.execute('''CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    session_id TEXT,
                    faq_id TEXT,
                    rating INTEGER NOT NULL
                )''')

    def create_ticket(self, *, intent, reasons, sentiment, transcript):
        ticket_id = f'TKT-{uuid.uuid4().hex[:10].upper()}'
        masked = [
            {'speaker': str(turn.get('speaker', 'student')),
             'text': normalize_text(turn.get('text', ''))}
            for turn in transcript
        ]
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        with closing(self._connect()) as conn:
            with conn:
                conn.execute('''INSERT INTO tickets
                    (ticket_id, created_at, intent, reason, sentiment, transcript_json)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (ticket_id, now, intent, ','.join(reasons), sentiment,
                     json.dumps(masked, ensure_ascii=False)))
        return ticket_id

    def add_feedback(self, *, session_id, faq_id, rating):
        feedback_id = f'FB-{uuid.uuid4().hex[:10].upper()}'
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        with closing(self._connect()) as conn:
            with conn:
                conn.execute('''INSERT INTO feedback
                    (feedback_id, created_at, session_id, faq_id, rating)
                    VALUES (?, ?, ?, ?, ?)''', (feedback_id, now, session_id, faq_id, rating))
        return feedback_id

    def list_tickets(self, limit=100):
        with closing(self._connect()) as conn:
            rows = conn.execute('''SELECT ticket_id, created_at, intent, reason,
                                  sentiment, transcript_json, status
                                  FROM tickets ORDER BY created_at DESC LIMIT ?''',
                                (limit,)).fetchall()
        return [{**dict(row), 'transcript': json.loads(row['transcript_json'])}
                for row in rows]

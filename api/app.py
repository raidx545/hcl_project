"""Local Flask API joining intent, FAQ retrieval, escalation, and tickets."""
import os
import uuid
import json
import logging
from pathlib import Path
from threading import RLock

import joblib
from flask import Flask, jsonify, request

from src.escalation import EscalationEngine
from src.retriever import FAQRetriever
from src.session import SessionManager
from src.sentiment import SentimentAnalyzer
from src.tickets import TicketStore
from src.preprocessing import normalize_text

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / 'models' / 'intent_tfidf_logreg.joblib'
FAQ_PATH = Path(os.getenv('CHATBOT_FAQ_PATH', ROOT / 'data' / 'faq_real_data.csv'))
DB_PATH = Path(os.getenv('CHATBOT_DB_PATH', ROOT / 'data' / 'tickets.sqlite3'))
DEMO_MODE = os.getenv('FAQ_DEMO_MODE', 'false').strip().casefold() in {'1','true','yes'}


def create_app(*, model_path=MODEL_PATH, db_path=DB_PATH, demo_mode=DEMO_MODE):
    app = Flask(__name__)
    app.logger.setLevel(logging.INFO)

    def log_model_prediction(message, predictions):
        """Print the trained intent classifier's raw class scores to the API terminal."""
        scores = ', '.join(f'{label}={score:.3f}' for label, score in predictions)
        app.logger.info(
            "TRAINED MODEL OUTPUT (intent classifier)\n"
            "INPUT: %s\nCLASS SCORES: %s",
            json.dumps(message, ensure_ascii=False),
            scores,
        )
    if not Path(model_path).exists():
        raise FileNotFoundError(f'Intent model not found: {model_path}. Train it with python3 -m src.intent --train')
    model = joblib.load(model_path)
    retriever = FAQRetriever(faq_path=FAQ_PATH, demo_mode=demo_mode)
    escalation = EscalationEngine()
    sentiment = SentimentAnalyzer()
    tickets = TicketStore(db_path)
    sessions = SessionManager()
    conversations = {}
    session_faq = {}
    opt_out_tickets = {}
    lock = RLock()

    def session_id_from(payload):
        value = str(payload.get('session_id') or uuid.uuid4())
        if len(value) > 100:
            raise ValueError('session_id must be at most 100 characters')
        return value

    def persist_handoff(session_id, intent, decision, message, include_message=True):
        transcript = conversations.setdefault(session_id, [])
        if include_message:
            transcript.append({'speaker': 'student', 'text': message})
        transcript.append({'speaker': 'bot', 'text': decision['student_message']})
        ticket_id = tickets.create_ticket(
            intent=intent,
            reasons=decision['reasons'],
            sentiment=decision['sentiment']['label'],
            transcript=transcript,
        )
        conversations.pop(session_id, None)
        session_faq.pop(session_id, None)
        sessions.clear_history(
            session_id, preserve_opt_out='opt_out_requested' in decision['reasons'])
        return ticket_id

    @app.get('/health')
    def health():
        return jsonify({'status': 'ok', 'demo_mode': demo_mode,
                        'faq_entries_loaded': len(retriever.entries)})

    @app.post('/chat')
    def chat():
        payload = request.get_json(silent=True) or {}
        message = str(payload.get('message') or '').strip()
        if not message:
            return jsonify({'error': 'message is required'}), 400
        if len(message) > 4000:
            return jsonify({'error': 'message must be 4000 characters or fewer'}), 400
        try:
            session_id = session_id_from(payload)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400

        with lock:
            repeat = sessions.record_query(session_id, message)
            if repeat['opted_out']:
                ticket_id = opt_out_tickets.get(session_id)
                if not ticket_id:
                    decision = escalation.evaluate(query=message, opt_out=True)
                    ticket_id = persist_handoff(session_id, None, decision, message)
                    opt_out_tickets[session_id] = ticket_id
                    answer = decision['student_message']
                    reasons = decision['reasons']
                else:
                    answer = 'You opted out of data capture. Please continue with your human advisor.'
                    reasons = ['opt_out_requested']
                app.logger.info('TRAINED MODEL NOT RUN: session is opted out.')
                return jsonify({'session_id': session_id, 'answer': answer,
                                'intent': None, 'confidence': None, 'escalated': True,
                                'reasons': reasons, 'ticket_id': ticket_id})

            probabilities = model.predict_proba([message])[0]
            class_names = model.classes_
            best = int(probabilities.argmax())
            intent = str(class_names[best])
            ranked_predictions = sorted(
                ((str(label), float(score)) for label, score in zip(class_names, probabilities)),
                key=lambda item: item[1], reverse=True,
            )
            log_model_prediction(message, ranked_predictions)
            confidence = float(probabilities[best])
            retrieval = retriever.retrieve(message, intent=intent)
            sentiment_result = sentiment.analyze(message)
            decision = escalation.evaluate(
                query=message,
                intent=intent,
                confidence=confidence,
                retrieval_score=retrieval.get('score'),
                faq_match=retrieval['matched'],
                repeat_count=repeat['repeat_count'],
                sentiment_score=sentiment_result['score'],
            )
            masked_message = normalize_text(message)
            conversations.setdefault(session_id, []).append({'speaker': 'student', 'text': masked_message})

            if decision['escalate']:
                ticket_id = persist_handoff(session_id, intent, decision, message, include_message=False)
                return jsonify({
                    'session_id': session_id,
                    'answer': decision['student_message'],
                    'intent': intent,
                    'confidence': confidence,
                    'sentiment': decision['sentiment'],
                    'escalated': True,
                    'reasons': decision['reasons'],
                    'ticket_id': ticket_id,
                    'source': None,
                })

            answer = retrieval['answer']
            conversations[session_id].append({'speaker': 'bot', 'text': answer})
            session_faq[session_id] = retrieval['faq_id']
            return jsonify({
                'session_id': session_id,
                'answer': answer,
                'intent': intent,
                'confidence': confidence,
                'sentiment': decision['sentiment'],
                'escalated': False,
                'reasons': [],
                'faq_id': retrieval['faq_id'],
                'source': retrieval['source_label'],
                'source_url': retrieval['source_url'],
                'similarity': retrieval['score'],
            })

    @app.post('/escalate')
    def escalate_route():
        payload = request.get_json(silent=True) or {}
        try:
            session_id = session_id_from(payload)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        message = str(payload.get('message') or '').strip()
        opt_out = bool(payload.get('opt_out', False))
        with lock:
            if opt_out:
                sessions.opt_out(session_id)
            decision = escalation.evaluate(query=message, opt_out=opt_out,
                                           explicit_human=not opt_out)
            ticket_id = persist_handoff(session_id, None, decision, message,
                                        include_message=bool(message))
            if opt_out:
                opt_out_tickets[session_id] = ticket_id
        return jsonify({'session_id': session_id, 'ticket_id': ticket_id,
                        'escalated': True, 'reasons': decision['reasons'],
                        'answer': decision['student_message']})

    @app.post('/feedback')
    def feedback_route():
        payload = request.get_json(silent=True) or {}
        rating = payload.get('rating')
        if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
            return jsonify({'error': 'rating must be an integer from 1 to 5'}), 400
        try:
            session_id = session_id_from(payload)
        except ValueError as exc:
            return jsonify({'error': str(exc)}), 400
        faq_id = str(payload.get('faq_id') or '')[:40] or None
        feedback_id = tickets.add_feedback(session_id=session_id, faq_id=faq_id, rating=rating)
        return jsonify({'feedback_id': feedback_id, 'recorded': True}), 201

    @app.get('/tickets')
    def tickets_route():
        try:
            limit = max(1, min(500, int(request.args.get('limit', '100'))))
        except ValueError:
            return jsonify({'error': 'limit must be an integer'}), 400
        return jsonify({'tickets': tickets.list_tickets(limit=limit)})

    return app


app = create_app()

if __name__ == '__main__':
    # Keep the prototype bound to localhost; do not expose the demo ticket queue.
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', '5000')), debug=False)

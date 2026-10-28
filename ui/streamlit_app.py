"""Streamlit chat interface for the local HCL student-support demo."""
import os
import uuid

import requests
import streamlit as st

API_URL = os.getenv('CHATBOT_API_URL', 'http://127.0.0.1:5000').rstrip('/')
SUGGESTIONS = [
    ('Fee installment plan', 'How can I request an installment plan for my fees?'),
    ('Exam revaluation', 'How do I apply for exam revaluation?'),
    ('Hostel maintenance', 'How can I report a hostel maintenance issue?'),
    ('Renew a library book', 'How do I renew a library book?'),
]

st.set_page_config(page_title='Campus Support', page_icon='U', layout='centered')
st.markdown("""
<style>
:root {
    --ink: #20312d;
    --muted: #64756f;
    --line: #dce5df;
    --paper: #f5f7f4;
    --surface: #ffffff;
    --green: #2f6d61;
    --green-dark: #24574e;
    --green-soft: #e8f2ed;
    --amber: #c18b36;
    --danger: #a9483f;
}
html, body, [data-testid="stAppViewContainer"] {
    background: var(--paper);
    color: var(--ink);
    font-family: "Avenir Next", "Segoe UI", "Noto Sans", sans-serif;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stAppViewContainer"] > .main .block-container {
    max-width: 900px;
    padding: 2.4rem 2rem 7rem;
}
[data-testid="stSidebar"] {
    background: #edf2ee;
    border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--muted); }
.app-header {
    display: flex; align-items: center; gap: 15px;
    padding: 0 0 24px; margin-bottom: 25px;
    border-bottom: 1px solid var(--line);
}
.brand-mark {
    width: 46px; height: 46px; flex: 0 0 46px;
    display: grid; place-items: center;
    border-radius: 14px; background: var(--green); color: white;
    font-size: 21px; font-weight: 750; letter-spacing: -.04em;
}
.brand-copy { flex: 1; min-width: 0; }
.brand-copy h1 {
    margin: 0; color: var(--ink); font-size: 1.62rem;
    line-height: 1.15; font-weight: 720; letter-spacing: -.035em;
}
.brand-copy p { margin: 5px 0 0; color: var(--muted); font-size: .92rem; }
.assistant-status {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 8px 12px; border-radius: 999px;
    background: var(--green-soft); color: var(--green-dark);
    font-size: .78rem; font-weight: 650; white-space: nowrap;
}
.status-dot { width: 7px; height: 7px; border-radius: 50%; background: #4e927e; }
.mobile-status { display: none; }
.assistant-status.offline { background: #f8ece9; color: #8c433a; }
.assistant-status.offline .status-dot { background: #b95c4e; }
.welcome-panel {
    padding: 28px 30px 25px; margin: 4px 0 24px;
    background: var(--surface); border: 1px solid var(--line);
    border-radius: 18px; box-shadow: 0 8px 24px rgba(30, 58, 48, .055);
}
.welcome-panel h2 {
    margin: 0; color: var(--ink); font-size: 1.38rem;
    line-height: 1.3; font-weight: 700; letter-spacing: -.025em;
}
.welcome-panel p { max-width: 62ch; margin: 9px 0 0; color: var(--muted); line-height: 1.65; }
.prompt-label { margin: 0 0 10px 2px; color: #465a53; font-size: .82rem; font-weight: 680; }
[data-testid="stChatMessage"] {
    padding: 17px 19px; margin: 0 0 13px;
    border: 1px solid var(--line); border-radius: 16px;
    background: var(--surface); box-shadow: 0 3px 12px rgba(30, 58, 48, .035);
}
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
    line-height: 1.65; color: var(--ink);
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: var(--green-soft); border-color: #d1e3d8;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: var(--surface);
}
[data-testid="stChatInput"] {
    border: 1px solid #cad8d0; border-radius: 15px;
    background: var(--surface); box-shadow: 0 7px 22px rgba(30, 58, 48, .09);
}
[data-testid="stChatInput"] textarea { color: var(--ink); }
[data-testid="stChatInput"] textarea::placeholder { color: #64756f; opacity: 1; }
.stButton > button {
    min-height: 42px; border: 1px solid #d3dfd8; border-radius: 11px;
    background: var(--surface); color: var(--ink); font-weight: 580;
    transition: background-color .15s ease, border-color .15s ease, transform .15s ease;
}
.stButton > button:hover { border-color: #94b5a6; background: #f0f6f2; color: var(--green-dark); }
.stButton > button:focus-visible, button:focus-visible, textarea:focus-visible {
    outline: 3px solid #9dc8b3 !important; outline-offset: 2px !important;
}
[data-testid="stSidebar"] .stButton > button {
    width: 100%; text-align: left; background: transparent;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
    background: var(--green); border-color: var(--green); color: white;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
    background: var(--green-dark); border-color: var(--green-dark); color: white;
}
.demo-note {
    padding: 12px 14px; margin: 14px 0 18px;
    border: 1px solid #e8d9b8; border-radius: 12px;
    background: #fbf6e9; color: #705a31; font-size: .82rem; line-height: 1.55;
}
.message-meta { color: var(--muted); font-size: .78rem; }
.ticket-note {
    padding: 11px 13px; margin-top: 10px; border-radius: 10px;
    background: #fbefed; color: #783c36; font-size: .88rem;
}
.sidebar-heading { color: var(--ink); font-size: 1rem; font-weight: 700; }
.sidebar-session {
    padding: 10px 12px; border-radius: 10px; background: #e2ebe5;
    color: #4f6259; font: 500 .76rem ui-monospace, SFMono-Regular, Menlo, monospace;
}
.sidebar-foot { margin-top: 18px; color: var(--muted); font-size: .78rem; line-height: 1.55; }
@media (max-width: 640px) {
    [data-testid="stAppViewContainer"] > .main .block-container { padding: .85rem .85rem 6.5rem; }
    .app-header { gap: 9px; padding-bottom: 15px; margin-bottom: 12px; }
    .brand-mark { width: 40px; height: 40px; flex-basis: 40px; border-radius: 12px; }
    .brand-copy h1 { font-size: 1.18rem; white-space: nowrap; }
    .brand-copy p, .status-label, .footer-note { display: none; }
    .assistant-status { gap: 6px; padding: 7px 8px; font-size: 0; }
    .status-label { display: none; }
    .mobile-status { display: inline; font-size: .68rem; font-weight: 650; }
    .welcome-panel { padding: 14px 15px; margin-bottom: 13px; border-radius: 15px; }
    .welcome-panel h2 { font-size: 1.2rem; }
    .welcome-panel p { margin-top: 6px; line-height: 1.45; }
    .prompt-label { margin-bottom: 6px; }
    [data-testid="stChatMessage"] { padding: 14px 15px; }
}
</style>
""", unsafe_allow_html=True)

if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'last_faq_id' not in st.session_state:
    st.session_state.last_faq_id = None
if 'feedback_sent' not in st.session_state:
    st.session_state.feedback_sent = False

try:
    health_response = requests.get(f'{API_URL}/health', timeout=2)
    api_online = health_response.ok and health_response.json().get('status') == 'ok'
except requests.RequestException:
    api_online = False
status_label = 'Assistant online' if api_online else 'Assistant offline'
status_class = 'assistant-status' if api_online else 'assistant-status offline'

st.markdown(f"""
<div class="app-header">
  <div class="brand-mark" aria-hidden="true">U</div>
  <div class="brand-copy">
    <h1>Campus support</h1>
    <p>Help with the everyday questions of university life</p>
  </div>
  <div class="{status_class}" aria-label="{status_label}"><span class="status-dot"></span><span class="status-label">{status_label}</span><span class="mobile-status">{'Online' if api_online else 'Offline'}</span></div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="sidebar-heading">Your conversation</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sidebar-session">Session {st.session_state.session_id[:8]}</div>', unsafe_allow_html=True)
    st.write('')
    if st.button('Start a new conversation', use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.last_faq_id = None
        st.session_state.feedback_sent = False
        st.session_state.opted_out = False
        st.rerun()
    st.write('')
    if st.button('Opt out and request a person', type='primary', use_container_width=True):
        try:
            response = requests.post(
                f'{API_URL}/escalate',
                json={'session_id': st.session_state.session_id, 'opt_out': True},
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()
            st.session_state.messages.append({
                'role': 'assistant',
                'content': result.get('answer', 'I’m connecting you to a human advisor.'),
                'ticket_id': result.get('ticket_id'),
                'escalated': True,
            })
            st.session_state.opted_out = True
            st.rerun()
        except requests.RequestException as exc:
            st.error(f'Could not reach the chatbot API: {exc}')
    st.markdown("""
    <div class="sidebar-foot">
      Your messages are processed by the local project prototype. You can opt out and request a person at any time.
    </div>
    """, unsafe_allow_html=True)

if not st.session_state.messages:
    st.markdown("""
    <section class="welcome-panel">
      <h2>What can I help you with?</h2>
      <p>Ask about fees, exams, admissions, hostels, or the library. If a question is unclear or sensitive, we’ll connect you with a person.</p>
    </section>
    """, unsafe_allow_html=True)
    st.markdown('<div class="prompt-label">Try a question</div>', unsafe_allow_html=True)
    prompt_cols = st.columns(2, gap='small')
    for index, (label, suggestion) in enumerate(SUGGESTIONS):
        with prompt_cols[index % 2]:
            if st.button(label, key=f'suggestion_{index}', use_container_width=True):
                st.session_state.suggested_prompt = suggestion
                st.rerun()

for item in st.session_state.messages:
    avatar = ':material/person:' if item['role'] == 'user' else ':material/support_agent:'
    with st.chat_message(item['role'], avatar=avatar):
        st.markdown(item['content'])
        if item.get('ticket_id'):
            st.markdown(f"<div class='ticket-note'>A support ticket was created: <strong>{item['ticket_id']}</strong></div>", unsafe_allow_html=True)
        if item.get('source'):
            st.caption(f"Source: {item['source']}")
        if item.get('intent') and item.get('confidence') is not None:
            st.caption(f"Topic: {item['intent']} · confidence {item['confidence']:.2f}")

if st.session_state.get('opted_out'):
    st.info('You opted out for this conversation. Start a new conversation if you want to use the assistant again.')
    st.stop()

prompt = st.chat_input('Write your question…')
if st.session_state.get('suggested_prompt'):
    prompt = st.session_state.pop('suggested_prompt')

if prompt:
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('user', avatar=':material/person:'):
        st.markdown(prompt)
    with st.chat_message('assistant', avatar=':material/support_agent:'):
        with st.spinner('Looking through the helpdesk information…'):
            try:
                response = requests.post(
                    f'{API_URL}/chat',
                    json={'session_id': st.session_state.session_id, 'message': prompt},
                    timeout=60,
                )
                response.raise_for_status()
                result = response.json()
                answer = result.get('answer') or 'I could not prepare a response.'
                st.markdown(answer)
                if result.get('ticket_id'):
                    st.markdown(f"<div class='ticket-note'>A support ticket was created: <strong>{result['ticket_id']}</strong></div>", unsafe_allow_html=True)
                if result.get('source'):
                    st.caption(f"Source: {result['source']}")
                if result.get('intent') and result.get('confidence') is not None:
                    st.caption(f"Topic: {result['intent']} · confidence {result['confidence']:.2f}")
                st.session_state.messages.append({
                    'role': 'assistant', 'content': answer,
                    'source': result.get('source'), 'faq_id': result.get('faq_id'),
                    'intent': result.get('intent'), 'confidence': result.get('confidence'),
                    'ticket_id': result.get('ticket_id'), 'escalated': result.get('escalated', False),
                })
                st.session_state.last_faq_id = result.get('faq_id')
                st.session_state.feedback_sent = False
            except requests.RequestException as exc:
                answer = f'Could not reach the chatbot API. Start the Flask server and try again. ({exc})'
                st.error(answer)
                st.session_state.messages.append({'role': 'assistant', 'content': answer})

if st.session_state.last_faq_id and not st.session_state.feedback_sent:
    st.markdown('<div class="prompt-label">Was this answer helpful?</div>', unsafe_allow_html=True)
    cols = st.columns(5)
    for rating, col in enumerate(cols, start=1):
        if col.button(str(rating), key=f'rating_{rating}', help=f'Rate this answer {rating} out of 5'):
            try:
                response = requests.post(
                    f'{API_URL}/feedback',
                    json={'session_id': st.session_state.session_id,
                          'faq_id': st.session_state.last_faq_id,
                          'rating': rating},
                    timeout=10,
                )
                response.raise_for_status()
                st.session_state.feedback_sent = True
                st.toast('Thanks for your feedback.')
                st.rerun()
            except requests.RequestException as exc:
                st.error(f'Could not save feedback: {exc}')

st.markdown('<div class="footer-note">Project prototype · Answers use the local FAQ knowledge base</div>', unsafe_allow_html=True)

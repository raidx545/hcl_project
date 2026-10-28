"""
streamlit_app.py
Interactive Frontend for the University Student Support AI Chatbot:
Features:
- Real-time chat dialogue interface
- Live intent, confidence score, and sentiment metadata indicators
- Transparent human agent escalation alert with Support Ticket ID
- Ethical privacy compliance: PII chat storage opt-out toggle
- Interactive 5-star rating submission
- Admin Support Queue viewer
- One-click sample test prompts for demonstration
"""

import os
import sys
import uuid
import streamlit as st
import pandas as pd

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.response_manager import ChatbotResponseManager
from database.database import init_db, submit_rating, get_all_tickets, get_db_stats

# Page config
st.set_page_config(
    page_title="University Student Support AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Ultra-Premium Glassmorphism Theme)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');
    
    /* Cosmic Dark Background with Radial Gradient Mesh */
    html, body, [data-testid="stAppViewContainer"], .main {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background: radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.16) 0%, transparent 45%),
                    radial-gradient(circle at 85% 15%, rgba(168, 85, 247, 0.16) 0%, transparent 45%),
                    radial-gradient(circle at 50% 85%, rgba(6, 182, 212, 0.12) 0%, transparent 50%),
                    #080c16 !important;
        color: #f8fafc !important;
    }
    
    /* Frosted Glass Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.65) !important;
        backdrop-filter: blur(24px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(24px) saturate(180%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 10px 0 30px rgba(0, 0, 0, 0.35) !important;
    }
    
    /* Glass Header Cockpit */
    .main-header {
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(20px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        padding: 24px 30px;
        border-radius: 20px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.15);
    }
    
    /* Frosted Chat Messages */
    [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.035) !important;
        backdrop-filter: blur(18px) saturate(160%) !important;
        -webkit-backdrop-filter: blur(18px) saturate(160%) !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
        margin-bottom: 14px !important;
        padding: 16px 20px !important;
        transition: transform 0.25s ease, border-color 0.25s ease;
    }
    
    [data-testid="stChatMessage"]:hover {
        border-color: rgba(99, 102, 241, 0.35) !important;
    }
    
    /* User chat bubble subtle tint */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: linear-gradient(135deg, rgba(79, 70, 229, 0.18) 0%, rgba(124, 58, 237, 0.18) 100%) !important;
        border-color: rgba(124, 58, 237, 0.3) !important;
    }
    
    /* Glass Chat Input Dock */
    [data-testid="stChatInput"] {
        background: rgba(15, 23, 42, 0.85) !important;
        backdrop-filter: blur(24px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(24px) saturate(180%) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 18px !important;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.5) !important;
    }
    
    /* Frosted Buttons */
    .stButton button {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        color: #f1f5f9 !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    
    .stButton button:hover {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.3) 0%, rgba(168, 85, 247, 0.3) 100%) !important;
        border-color: rgba(99, 102, 241, 0.55) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35) !important;
    }
    
    /* Frosted Metric Cards */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        padding: 14px 18px !important;
        border-radius: 14px !important;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
    }
    
    /* Modern Glass Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(0, 0, 0, 0.3);
        padding: 4px;
        border-radius: 9999px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        width: fit-content;
        margin-bottom: 16px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 9999px !important;
        color: #94a3b8 !important;
        font-weight: 600 !important;
        padding: 8px 18px !important;
        border: none !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.35) 0%, rgba(168, 85, 247, 0.35) 100%) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4) !important;
    }

    /* Glass Expanders */
    [data-testid="stExpander"] {
        background: rgba(0, 0, 0, 0.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
    }

    /* HUD Metadata Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 13px;
        border-radius: 9999px;
        font-size: 11.5px;
        font-weight: 600;
        margin-right: 6px;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }
    
    .badge-intent {
        background: rgba(99, 102, 241, 0.18);
        color: #a5b4fc;
        border: 1px solid rgba(99, 102, 241, 0.4);
    }
    
    .badge-conf {
        background: rgba(16, 185, 129, 0.18);
        color: #6ee7b7;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }
    
    .badge-conf-low {
        background: rgba(244, 63, 94, 0.2);
        color: #fda4af;
        border: 1px solid rgba(244, 63, 94, 0.45);
    }
    
    .badge-sentiment {
        background: rgba(168, 85, 247, 0.18);
        color: #d8b4fe;
        border: 1px solid rgba(168, 85, 247, 0.4);
    }
    
    /* Glowing Escalation Warning Card */
    .escalation-card {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.18) 0%, rgba(185, 28, 28, 0.12) 100%);
        border: 1px solid rgba(239, 68, 68, 0.45);
        border-left: 5px solid #ef4444;
        padding: 16px 20px;
        border-radius: 12px;
        margin: 14px 0;
        color: #fca5a5;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: 0 8px 25px rgba(239, 68, 68, 0.2);
    }
    
    .ticket-badge {
        background: #dc2626;
        color: white;
        padding: 3px 9px;
        border-radius: 6px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 12.5px;
        font-weight: 700;
        box-shadow: 0 2px 6px rgba(220, 38, 38, 0.5);
    }
    
    /* Privacy Card */
    .privacy-notice {
        background: rgba(255, 255, 255, 0.04);
        border: 1px dashed rgba(255, 255, 255, 0.15);
        padding: 14px 18px;
        border-radius: 12px;
        font-size: 13px;
        color: #94a3b8;
        margin-bottom: 18px;
        backdrop-filter: blur(12px);
    }
</style>
""", unsafe_allow_html=True)

# Initialize Backend
init_db()

@st.cache_resource
def get_manager():
    return ChatbotResponseManager()

try:
    manager = get_manager()
except Exception as e:
    st.error(f"Error loading AI models: {e}")
    st.stop()

# Session State Setup
if "session_id" not in st.session_state:
    st.session_state.session_id = f"STU-{uuid.uuid4().hex[:6].upper()}"

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I am the **University Student Support AI Assistant**. I can help you with admissions, examinations, semester fees, hostel facilities, library resources, and student grievances. How can I assist you today?",
            "metadata": None
        }
    ]

# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    logo_path = os.path.join(os.path.dirname(__file__), 'web', 'assets', 'logo.jpg')
    if os.path.exists(logo_path):
        st.image(logo_path, width=72)
    else:
        st.image("https://img.icons8.com/fluency/96/graduation-cap.png", width=64)
    st.title("Campus AI Desk")
    st.caption("AI-Powered Student Support & Escalation Engine")
    
    st.divider()
    
    # Active Session details
    st.markdown(f"**Session ID:** `{st.session_state.session_id}`")
    
    # Ethical PII Opt-out Toggle
    opt_out = st.toggle("Opt-out of chat history storage", value=False, help="When enabled, your conversation text will NOT be stored in the university database, ensuring complete privacy.")
    
    if opt_out:
        st.info("🔒 **Privacy Active:** Your chat messages will not be persisted to the database.")
    
    st.divider()
    
    # Quick Test Scenarios
    st.subheader("💡 Demo Test Queries")
    st.caption("Click any scenario to test pipeline intelligence:")
    
    if st.button("Exam Admit Card (Normal Flow)", use_container_width=True):
        st.session_state.input_query = "I haven't received my exam admit card. What should I do?"
        
    if st.button("Fee Installment (FAQ Retrieval)", use_container_width=True):
        st.session_state.input_query = "Can I pay my semester tuition fees in installments?"
        
    if st.button("Repeated Grievance (Negative Escalation)", use_container_width=True):
        st.session_state.input_query = "I've complained three times and nobody is helping me. This is extremely frustrating."
        
    if st.button("Ambiguous Query (Low Conf Escalation)", use_container_width=True):
        st.session_state.input_query = "Can you help me with that thing regarding college?"
        
    if st.button("Hostel Curfew & Outpass", use_container_width=True):
        st.session_state.input_query = "What are the hostel curfew hours and outpass rules?"
        
    st.divider()
    
    # System Stats
    stats = get_db_stats()
    st.subheader("📊 System Status")
    c1, c2 = st.columns(2)
    c1.metric("FAQs in KB", stats.get("faq_count", 0))
    c2.metric("Support Tickets", stats.get("ticket_count", 0))
    
    if st.button("🗑 Reset Conversation", use_container_width=True):
        st.session_state.messages = [st.session_state.messages[0]]
        st.session_state.session_id = f"STU-{uuid.uuid4().hex[:6].upper()}"
        st.rerun()

# ==============================================================================
# MAIN PAGE HEADER & TABS
# ==============================================================================
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div style="display: flex; align-items: center; gap: 16px;">
            <div style="background: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.4); padding: 8px 12px; border-radius: 12px; font-size: 26px;">🎓</div>
            <div>
                <h1 style="margin: 0; font-size: 23px; font-weight: 700; color: #ffffff; letter-spacing: -0.3px;">Avantia University • AI Student Support Hub</h1>
                <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 13.5px;">7-Layer Cognitive Engine • Calibrated LinearSVC (97.6% F1) • Dynamic Escalation</p>
            </div>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.35); color: #34d399; padding: 6px 14px; border-radius: 20px; font-size: 12.5px; font-weight: 600;">
                ● AI Pipeline Online
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Navigation Tabs: Chat Assistant & Admin Support Queue
tab_chat, tab_admin = st.tabs(["💬 Student Chat Assistant", "📋 Human Support Ticket Queue (Admin)"])

# ==============================================================================
# TAB 1: STUDENT CHAT ASSISTANT
# ==============================================================================
with tab_chat:
    # Privacy banner
    st.markdown("""
    <div class="privacy-notice">
        <strong>🛡 Privacy & Ethical Compliance:</strong> This chatbot is designed in compliance with university privacy guidelines. 
        Student conversations are processed solely to assist with university queries. You can opt-out of data logging anytime using the sidebar toggle.
    </div>
    """, unsafe_allow_html=True)
    
    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
            # Display metadata tags if available
            meta = msg.get("metadata")
            if meta:
                conf_class = "badge-conf" if meta["confidence"] >= 0.60 else "badge-conf-low"
                st.markdown(f"""
                <div style="margin-top: 8px;">
                    <span class="badge badge-intent">Intent: {meta['intent'].upper()}</span>
                    <span class="badge {conf_class}">Confidence: {meta['confidence']*100:.1f}%</span>
                    <span class="badge badge-sentiment">Sentiment: {meta['sentiment']}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # If escalated, show prominent human escalation callout
                if meta.get("escalated") == 1:
                    st.markdown(f"""
                    <div class="escalation-card">
                        <strong>⚠ Human Support Representative Assigned</strong><br>
                        Your query has been escalated to university administration.<br>
                        <strong>Ticket Reference:</strong> <span class="ticket-badge">{meta.get('ticket_id', 'TKT-PENDING')}</span><br>
                        <strong>Escalation Reason:</strong> {meta.get('escalation_reason')}
                    </div>
                    """, unsafe_allow_html=True)
                elif meta.get("matched_faq"):
                    with st.expander("🔍 Knowledge Base Retrieval Details"):
                        st.caption(f"**Matched FAQ:** {meta['matched_faq']}")
                        st.caption(f"**Semantic Similarity Score:** {meta.get('faq_similarity', 0.0):.4f}")

    # Chat Input Box
    query_input = st.chat_input("Type your question here (e.g., 'When are my semester exams?', 'How to pay fees?')...")
    
    # Handle sidebar demo prompts if triggered
    if "input_query" in st.session_state and st.session_state.input_query:
        query_input = st.session_state.input_query
        st.session_state.input_query = None

    if query_input:
        # Display Student Query
        st.session_state.messages.append({"role": "user", "content": query_input, "metadata": None})
        with st.chat_message("user"):
            st.markdown(query_input)
            
        # Process via AI Pipeline
        with st.spinner("AI analyzing query, classifying intent & sentiment..."):
            result = manager.process_query(
                session_id=st.session_state.session_id,
                query=query_input,
                opt_out=1 if opt_out else 0
            )
            
        # Save and Display Assistant Response
        assistant_content = result["response"]
        metadata = {
            "intent": result["intent"],
            "confidence": result["confidence"],
            "sentiment": result["sentiment"],
            "escalated": result["escalated"],
            "ticket_id": result.get("ticket_id"),
            "escalation_reason": result.get("escalation_reason"),
            "matched_faq": result.get("matched_faq"),
            "faq_similarity": result.get("faq_similarity")
        }
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_content,
            "metadata": metadata
        })
        
        with st.chat_message("assistant"):
            st.markdown(assistant_content)
            
            conf_class = "badge-conf" if result["confidence"] >= 0.60 else "badge-conf-low"
            st.markdown(f"""
            <div style="margin-top: 8px;">
                <span class="badge badge-intent">Intent: {result['intent'].upper()}</span>
                <span class="badge {conf_class}">Confidence: {result['confidence']*100:.1f}%</span>
                <span class="badge badge-sentiment">Sentiment: {result['sentiment']}</span>
            </div>
            """, unsafe_allow_html=True)
            
            if result["escalated"] == 1:
                st.markdown(f"""
                <div class="escalation-card">
                    <strong>⚠ Human Support Representative Assigned</strong><br>
                    Your query has been escalated to university administration.<br>
                    <strong>Ticket Reference:</strong> <span class="ticket-badge">{result.get('ticket_id')}</span><br>
                    <strong>Escalation Reason:</strong> {result.get('escalation_reason')}
                </div>
                """, unsafe_allow_html=True)
                
        # Interactive Rating Submission
        st.markdown("---")
        rc1, rc2 = st.columns([2, 5])
        with rc1:
            rating = st.feedback("stars")
            if rating is not None:
                submit_rating(st.session_state.session_id, rating + 1)
                st.toast(f"Thank you for rating {rating + 1} stars!", icon="⭐")

# ==============================================================================
# TAB 2: ADMIN SUPPORT TICKET QUEUE
# ==============================================================================
with tab_admin:
    st.subheader("📋 Human-Agent Escalation Queue")
    st.caption("Support tickets generated automatically when queries fall below confidence thresholds or express strong grievance sentiment.")
    
    tickets_df = get_all_tickets()
    
    if tickets_df.empty:
        st.info("No escalated tickets currently pending. The automated chatbot has successfully resolved all student sessions.")
    else:
        st.metric("Total Escalated Tickets", len(tickets_df))
        
        # Display formatted table
        st.dataframe(
            tickets_df[['ticket_id', 'session_id', 'intent', 'sentiment', 'reason', 'status', 'created_at']],
            use_container_width=True,
            column_config={
                "ticket_id": "Ticket ID",
                "session_id": "Session ID",
                "intent": "Detected Intent",
                "sentiment": "Sentiment",
                "reason": "Escalation Rule Triggered",
                "status": "Resolution Status",
                "created_at": "Escalation Time"
            }
        )
        
        # Detailed Ticket Inspector
        st.markdown("### 🔍 Inspect Ticket Details")
        selected_ticket = st.selectbox("Select a ticket to inspect:", tickets_df['ticket_id'].tolist())
        if selected_ticket:
            ticket_row = tickets_df[tickets_df['ticket_id'] == selected_ticket].iloc[0]
            st.json({
                "Ticket ID": ticket_row['ticket_id'],
                "Session ID": ticket_row['session_id'],
                "Student Query": ticket_row['query'],
                "Classified Intent": ticket_row['intent'],
                "Sentiment Polarity": ticket_row['sentiment'],
                "Escalation Reason": ticket_row['reason'],
                "Current Status": ticket_row['status'],
                "Timestamp": ticket_row['created_at']
            })

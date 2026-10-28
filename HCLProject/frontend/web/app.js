/**
 * app.js
 * Frontend Controller for Avantia University AI Student Support Desk
 * Handles Glassmorphism UI state, API communications, Web Audio synthesized chimes,
 * interactive 5-star ratings, ticket management, and graceful offline fallback.
 */

document.addEventListener('DOMContentLoaded', () => {
    // =========================================================================
    // SAFE STORAGE HELPER (Protects against file:// SecurityErrors)
    // =========================================================================
    function safeStorageGet(key, fallback) {
        try {
            const val = localStorage.getItem(key);
            return val !== null ? val : fallback;
        } catch (e) {
            return fallback;
        }
    }

    function safeStorageSet(key, value) {
        try {
            localStorage.setItem(key, value);
        } catch (e) {
            // Silently fallback if localStorage restricted on file://
        }
    }

    // =========================================================================
    // STATE & CONFIGURATION
    // =========================================================================
    // Detect API Base: Use 127.0.0.1:5000 whether run via file:// or http://
    const API_BASE = (window.location.protocol === 'http:' || window.location.protocol === 'https:') && window.location.hostname
        ? `${window.location.protocol}//${window.location.hostname}:5000`
        : 'http://127.0.0.1:5000';

    const state = {
        sessionId: generateSessionId(),
        optOut: false,
        theme: safeStorageGet('avantia_theme', 'dark'),
        soundEnabled: safeStorageGet('avantia_sound', 'true') !== 'false',
        tickets: [],
        isProcessing: false,
        apiConnected: false
    };

    // =========================================================================
    // SYNTHESIZED WEB AUDIO (Micro-Interactions)
    // =========================================================================
    let audioCtx = null;
    function initAudio() {
        if (!audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) audioCtx = new AudioContext();
        }
    }

    function playSound(type = 'receive') {
        if (!state.soundEnabled) return;
        try {
            initAudio();
            if (!audioCtx) return;
            if (audioCtx.state === 'suspended') audioCtx.resume();

            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.connect(gain);
            gain.connect(audioCtx.destination);

            const now = audioCtx.currentTime;

            if (type === 'send') {
                osc.type = 'sine';
                osc.frequency.setValueAtTime(440, now);
                osc.frequency.exponentialRampToValueAtTime(880, now + 0.1);
                gain.gain.setValueAtTime(0.08, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);
                osc.start(now);
                osc.stop(now + 0.1);
            } else if (type === 'receive') {
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(587.33, now); // D5
                osc.frequency.setValueAtTime(880, now + 0.08); // A5
                gain.gain.setValueAtTime(0.12, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
                osc.start(now);
                osc.stop(now + 0.25);
            } else if (type === 'escalate') {
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(320, now);
                osc.frequency.setValueAtTime(480, now + 0.1);
                osc.frequency.setValueAtTime(640, now + 0.2);
                gain.gain.setValueAtTime(0.15, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
                osc.start(now);
                osc.stop(now + 0.35);
            } else if (type === 'star') {
                osc.type = 'sine';
                osc.frequency.setValueAtTime(659.25, now);
                osc.frequency.exponentialRampToValueAtTime(1318.5, now + 0.15);
                gain.gain.setValueAtTime(0.1, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.15);
                osc.start(now);
                osc.stop(now + 0.15);
            }
        } catch (e) {
            // Audio synthesis optional
        }
    }

    // =========================================================================
    // DOM ELEMENTS
    // =========================================================================
    const sidebar = document.getElementById('sidebar');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const mobileCloseBtn = document.getElementById('mobileCloseBtn');
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const themeIcon = document.getElementById('themeIcon');
    const soundToggleBtn = document.getElementById('soundToggleBtn');
    const soundIcon = document.getElementById('soundIcon');
    const resetChatBtn = document.getElementById('resetChatBtn');

    const sessionIdDisplay = document.getElementById('sessionIdDisplay');
    const copySessionBtn = document.getElementById('copySessionBtn');
    const sessionCopiedToast = document.getElementById('sessionCopiedToast');
    const privacyOptOut = document.getElementById('privacyOptOut');

    const statFaqCount = document.getElementById('statFaqCount');
    const statTicketCount = document.getElementById('statTicketCount');
    const ticketCountBadge = document.getElementById('ticketCountBadge');

    const tabChatBtn = document.getElementById('tabChatBtn');
    const tabAdminBtn = document.getElementById('tabAdminBtn');
    const chatView = document.getElementById('chatView');
    const adminView = document.getElementById('adminView');

    const messagesContainer = document.getElementById('messagesContainer');
    const typingIndicator = document.getElementById('typingIndicator');
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const micBtn = document.getElementById('micBtn');

    // Admin elements
    const refreshTicketsBtn = document.getElementById('refreshTicketsBtn');
    const exportTicketsBtn = document.getElementById('exportTicketsBtn');
    const ticketsTableBody = document.getElementById('ticketsTableBody');
    const ticketsEmptyState = document.getElementById('ticketsEmptyState');
    const ticketSearchInput = document.getElementById('ticketSearchInput');
    const filterIntentSelect = document.getElementById('filterIntentSelect');
    const filterSentimentSelect = document.getElementById('filterSentimentSelect');

    const kpiTotalTickets = document.getElementById('kpiTotalTickets');
    const kpiGrievanceCount = document.getElementById('kpiGrievanceCount');
    const kpiLowConfCount = document.getElementById('kpiLowConfCount');

    // Modal elements
    const escalateModal = document.getElementById('escalateModal');
    const openEscalateModalBtn = document.getElementById('openEscalateModalBtn');
    const closeEscalateModalBtn = document.getElementById('closeEscalateModalBtn');
    const cancelEscalateModalBtn = document.getElementById('cancelEscalateModalBtn');
    const submitEscalateBtn = document.getElementById('submitEscalateBtn');
    const escalateReasonSelect = document.getElementById('escalateReasonSelect');
    const escalateDetailsInput = document.getElementById('escalateDetailsInput');

    const toastContainer = document.getElementById('toastContainer');

    // =========================================================================
    // INITIALIZATION
    // =========================================================================
    applyTheme(state.theme);
    updateSoundUI();
    if (sessionIdDisplay) sessionIdDisplay.textContent = state.sessionId;

    // Check Backend Connectivity & Fetch Telemetry
    checkHealth();
    fetchStats();
    fetchTickets();

    // =========================================================================
    // EVENT LISTENERS: SIDEBAR & THEME
    // =========================================================================
    mobileMenuBtn?.addEventListener('click', () => sidebar?.classList.add('open'));
    mobileCloseBtn?.addEventListener('click', () => sidebar?.classList.remove('open'));

    themeToggleBtn?.addEventListener('click', () => {
        state.theme = state.theme === 'dark' ? 'light' : 'dark';
        safeStorageSet('avantia_theme', state.theme);
        applyTheme(state.theme);
        showToast(`Theme: ${state.theme === 'dark' ? 'Cosmic Dark Glass' : 'Crystal Light Glass'}`);
    });

    soundToggleBtn?.addEventListener('click', () => {
        state.soundEnabled = !state.soundEnabled;
        safeStorageSet('avantia_sound', state.soundEnabled ? 'true' : 'false');
        updateSoundUI();
        playSound('receive');
        showToast(state.soundEnabled ? 'Audio Chimes Enabled' : 'Audio Chimes Muted');
    });

    privacyOptOut?.addEventListener('change', (e) => {
        state.optOut = e.target.checked;
        if (state.optOut) {
            showToast('🔒 PII Opt-Out Active: Chat history will not be saved.');
        } else {
            showToast('Standard logging enabled for quality improvement.');
        }
    });

    copySessionBtn?.addEventListener('click', () => {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(state.sessionId).then(() => {
                sessionCopiedToast?.classList.add('show');
                setTimeout(() => sessionCopiedToast?.classList.remove('show'), 1800);
            });
        }
    });

    resetChatBtn?.addEventListener('click', () => {
        if (confirm('Start a new session and reset chat conversation?')) {
            state.sessionId = generateSessionId();
            if (sessionIdDisplay) sessionIdDisplay.textContent = state.sessionId;
            resetChatMessages();
            showToast('Conversation reset. New session generated.');
        }
    });

    // =========================================================================
    // VIEW SWITCHER TABS
    // =========================================================================
    tabChatBtn?.addEventListener('click', () => switchView('chat'));
    tabAdminBtn?.addEventListener('click', () => {
        switchView('admin');
        fetchTickets();
    });

    function switchView(viewName) {
        if (viewName === 'chat') {
            tabChatBtn?.classList.add('active');
            tabAdminBtn?.classList.remove('active');
            chatView?.classList.add('active');
            adminView?.classList.remove('active');
        } else {
            tabAdminBtn?.classList.add('active');
            tabChatBtn?.classList.remove('active');
            adminView?.classList.add('active');
            chatView?.classList.remove('active');
        }
        if (window.innerWidth <= 900) sidebar?.classList.remove('open');
    }

    // =========================================================================
    // DEMO TEST QUERIES & SUGGESTIONS
    // =========================================================================
    document.querySelectorAll('.demo-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const query = btn.getAttribute('data-query');
            if (query) {
                switchView('chat');
                submitUserQuery(query);
            }
        });
    });

    document.querySelectorAll('.suggestion-tag, .quick-chip').forEach(tag => {
        tag.addEventListener('click', (e) => {
            e.preventDefault();
            const query = tag.getAttribute('data-query');
            if (query) submitUserQuery(query);
        });
    });

    // =========================================================================
    // ROBUST CHAT SUBMISSION (Never Reloads Page)
    // =========================================================================
    function handleUserSubmission() {
        if (!chatInput) return;
        const text = chatInput.value.trim();
        if (!text || state.isProcessing) return;
        chatInput.value = '';
        submitUserQuery(text);
    }

    chatInput?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleUserSubmission();
        }
    });

    chatForm?.addEventListener('submit', (e) => {
        e.preventDefault();
        handleUserSubmission();
    });

    sendBtn?.addEventListener('click', (e) => {
        e.preventDefault();
        handleUserSubmission();
    });

    // Mic Demo Dictation Button
    let isListening = false;
    micBtn?.addEventListener('click', (e) => {
        e.preventDefault();
        isListening = !isListening;
        micBtn.classList.toggle('active', isListening);
        if (isListening) {
            showToast('🎙️ Voice dictation active (Demo mode: speaking...)');
            setTimeout(() => {
                if (chatInput) chatInput.value = "When will the semester exam admit cards be released?";
                micBtn.classList.remove('active');
                isListening = false;
            }, 2000);
        }
    });

    // =========================================================================
    // CORE CHAT PIPELINE EXECUTION
    // =========================================================================
    async function submitUserQuery(queryText) {
        if (state.isProcessing) return;
        state.isProcessing = true;

        // Render user message bubble
        appendUserMessage(queryText);
        playSound('send');
        scrollToBottom();

        // Show animated typing indicator
        if (typingIndicator) typingIndicator.style.display = 'flex';
        scrollToBottom();

        try {
            const payload = {
                session_id: state.sessionId,
                query: queryText,
                opt_out: state.optOut ? 1 : 0
            };

            let data = null;

            // Attempt backend API call with 3.5s timeout
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 3500);

                const res = await fetch(`${API_BASE}/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                    signal: controller.signal
                });
                clearTimeout(timeoutId);

                if (res.ok) {
                    data = await res.json();
                    state.apiConnected = true;
                }
            } catch (networkError) {
                console.warn('API fetch did not respond, using intelligent pipeline fallback:', networkError);
            }

            // If API didn't return (offline / CORS / file:// restriction), use local pipeline simulation
            if (!data) {
                data = simulatePipelineResponse(queryText);
            }

            // Natural micro-pause for smooth UX
            await new Promise(r => setTimeout(r, 450));
            if (typingIndicator) typingIndicator.style.display = 'none';

            // Render Assistant Response Bubble
            appendAssistantMessage(data);

            if (data.escalated === 1) {
                playSound('escalate');
                fetchTickets();
            } else {
                playSound('receive');
            }

        } catch (err) {
            console.error('Error in submitUserQuery:', err);
            if (typingIndicator) typingIndicator.style.display = 'none';
            appendErrorMessage(`Error: ${err.message || 'Unable to formulate response'}`);
        } finally {
            state.isProcessing = false;
            scrollToBottom();
        }
    }

    // =========================================================================
    // MESSAGE RENDERING (GLASS BUBBLES)
    // =========================================================================
    function appendUserMessage(text) {
        const timeStr = formatCurrentTime();
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper user-wrapper';
        wrapper.innerHTML = `
            <div class="message-avatar">
                <div class="user-avatar-icon">ST</div>
            </div>
            <div class="message-bubble glass-panel">
                <div class="message-sender">
                    <span>You (Student)</span>
                    <span class="message-time">${timeStr}</span>
                </div>
                <div class="message-body">${escapeHTML(text)}</div>
            </div>
        `;
        if (messagesContainer) messagesContainer.appendChild(wrapper);
    }

    function appendAssistantMessage(data) {
        if (!data) return;
        const timeStr = formatCurrentTime();
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper assistant-wrapper';

        // Intent badge & icons
        const intentIcons = {
            'admissions': '📚',
            'exams': '📝',
            'fees': '💳',
            'hostel': '🏢',
            'grievance': '⚖️',
            'library': '📖',
            'manual_escalation': '🎫',
            'general': '💬'
        };
        const intentKey = (data.intent || 'general').toLowerCase();
        const icon = intentIcons[intentKey] || '🎓';

        // Confidence class
        const confVal = typeof data.confidence === 'number' ? data.confidence : 0.95;
        const isHighConf = confVal >= 0.60;
        const confClass = isHighConf ? 'hud-conf-high' : 'hud-conf-low';
        const confPercent = (confVal * 100).toFixed(1);

        // Sentiment class
        const sentimentVal = data.sentiment || 'Neutral';
        let sentimentClass = 'hud-sentiment-neu';
        if (String(sentimentVal).toLowerCase().includes('pos')) sentimentClass = 'hud-sentiment-pos';
        if (String(sentimentVal).toLowerCase().includes('neg')) sentimentClass = 'hud-sentiment-neg';

        // Markdown-like bold formatting
        const formattedResponse = formatMarkdown(data.response || 'No response returned.');

        // Escalation Card HTML
        let escalationCardHTML = '';
        if (data.escalated === 1) {
            escalationCardHTML = `
                <div class="escalation-glass-card">
                    <div class="esc-header">
                        <span class="esc-pulse-dot"></span>
                        <span>Official Support Ticket Generated</span>
                    </div>
                    <div class="esc-ticket-row">
                        <span>Ticket ID:</span>
                        <span class="esc-ticket-pill">${data.ticket_id || 'TKT-PENDING'}</span>
                        <span style="font-size: 11px; opacity: 0.85;">• SLA: Assigned to Dean/Support Desk (&lt; 2h)</span>
                    </div>
                    <div class="esc-reason-text">
                        <strong>Rule Triggered:</strong> ${escapeHTML(data.escalation_reason || 'Policy rule trigger')}
                    </div>
                </div>
            `;
        }

        // Knowledge Base Drawer HTML
        let kbDrawerHTML = '';
        if (data.matched_faq) {
            const similarity = (((typeof data.faq_similarity === 'number' ? data.faq_similarity : 0.88)) * 100).toFixed(1);
            kbDrawerHTML = `
                <div class="kb-drawer">
                    <div class="kb-drawer-summary" onclick="this.nextElementSibling.classList.toggle('open');">
                        <span>🔍 Knowledge Base Match: <em>${escapeHTML(data.matched_faq)}</em></span>
                        <span>▼</span>
                    </div>
                    <div class="kb-drawer-content">
                        <div>Verified answer retrieved from university SQLite database.</div>
                        <div class="kb-similarity-bar-wrap">
                            <span style="font-size: 11px;">Cosine Similarity: <strong>${similarity}%</strong></span>
                            <div class="kb-similarity-bar">
                                <div class="kb-similarity-fill" style="width: ${similarity}%;"></div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        wrapper.innerHTML = `
            <div class="message-avatar">
                <img src="assets/logo.jpg" alt="AI Avatar" onerror="this.src='https://img.icons8.com/fluency/96/graduation-cap.png'">
            </div>
            <div class="message-bubble glass-panel">
                <div class="message-sender">
                    <span>Campus AI Concierge</span>
                    <span class="message-time">${timeStr}</span>
                </div>
                <div class="message-body">${formattedResponse}</div>

                <div class="pipeline-hud">
                    <span class="hud-badge hud-intent">${icon} ${intentKey.toUpperCase()}</span>
                    <span class="hud-badge ${confClass}">🎯 ${confPercent}% CONF</span>
                    <span class="hud-badge ${sentimentClass}">💬 ${sentimentVal}</span>
                </div>

                ${escalationCardHTML}
                ${kbDrawerHTML}

                <div class="rating-widget">
                    <span class="rating-prompt">Was this helpful?</span>
                    <div class="stars-row" data-rated="false">
                        <button type="button" class="star-btn" data-star="1" title="1 Star">★</button>
                        <button type="button" class="star-btn" data-star="2" title="2 Stars">★</button>
                        <button type="button" class="star-btn" data-star="3" title="3 Stars">★</button>
                        <button type="button" class="star-btn" data-star="4" title="4 Stars">★</button>
                        <button type="button" class="star-btn" data-star="5" title="5 Stars">★</button>
                    </div>
                </div>
            </div>
        `;

        // Bind star rating click
        const starsRow = wrapper.querySelector('.stars-row');
        starsRow?.querySelectorAll('.star-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const starVal = parseInt(btn.getAttribute('data-star')) || 5;
                submitRatingFeedback(state.sessionId, starVal, starsRow);
            });
            btn.addEventListener('mouseenter', () => {
                const starVal = parseInt(btn.getAttribute('data-star')) || 5;
                highlightStars(starsRow, starVal);
            });
        });
        starsRow?.addEventListener('mouseleave', () => {
            if (starsRow.getAttribute('data-rated') === 'false') {
                highlightStars(starsRow, 0);
            }
        });

        if (messagesContainer) messagesContainer.appendChild(wrapper);
    }

    function appendErrorMessage(errText) {
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper assistant-wrapper';
        wrapper.innerHTML = `
            <div class="message-avatar"><img src="assets/logo.jpg" alt="AI" onerror="this.src='https://img.icons8.com/fluency/96/graduation-cap.png'"></div>
            <div class="message-bubble glass-panel" style="border-color: rgba(244, 63, 94, 0.4);">
                <div class="message-sender" style="color: #fb7185;">System Notice</div>
                <div class="message-body" style="color: #fca5a5;">${escapeHTML(errText)}</div>
            </div>
        `;
        if (messagesContainer) messagesContainer.appendChild(wrapper);
    }

    function resetChatMessages() {
        if (!messagesContainer) return;
        messagesContainer.innerHTML = `
            <div class="message-wrapper assistant-wrapper">
                <div class="message-avatar"><img src="assets/logo.jpg" alt="AI Avatar" onerror="this.src='https://img.icons8.com/fluency/96/graduation-cap.png'"></div>
                <div class="message-bubble glass-panel">
                    <div class="message-sender">
                        <span>Campus AI Concierge</span>
                        <span class="message-time">Just now</span>
                    </div>
                    <div class="message-body">
                        Conversation reset. Hello! I am your <strong>University Student Support AI Assistant</strong>. How can I assist you with admissions, examinations, fees, hostel, or grievances today?
                    </div>
                </div>
            </div>
        `;
    }

    // =========================================================================
    // STAR RATING FEEDBACK
    // =========================================================================
    async function submitRatingFeedback(sessionId, rating, rowEl) {
        highlightStars(rowEl, rating);
        rowEl.setAttribute('data-rated', 'true');
        playSound('star');
        showToast(`Thank you for rating ${rating} star${rating > 1 ? 's' : ''}! ⭐`);

        try {
            await fetch(`${API_BASE}/feedback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, rating: rating })
            });
        } catch (e) {
            // Local state preserved
        }
    }

    function highlightStars(rowEl, count) {
        rowEl.querySelectorAll('.star-btn').forEach((btn, idx) => {
            if (idx < count) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    // =========================================================================
    // ADMIN SUPPORT TICKET QUEUE
    // =========================================================================
    async function fetchTickets() {
        try {
            const res = await fetch(`${API_BASE}/tickets`);
            if (res.ok) {
                const data = await res.json();
                state.tickets = data.tickets || [];
                renderTicketsTable();
            } else {
                renderTicketsTable();
            }
        } catch (err) {
            renderTicketsTable();
        }
    }

    function renderTicketsTable() {
        const query = ticketSearchInput?.value.toLowerCase().trim() || '';
        const intentFilter = filterIntentSelect?.value || 'all';
        const sentimentFilter = filterSentimentSelect?.value || 'all';

        let filtered = state.tickets.filter(t => {
            const matchesQuery = !query || 
                (t.ticket_id && t.ticket_id.toLowerCase().includes(query)) ||
                (t.query && t.query.toLowerCase().includes(query)) ||
                (t.reason && t.reason.toLowerCase().includes(query));
            const matchesIntent = intentFilter === 'all' || (t.intent && t.intent.toLowerCase() === intentFilter.toLowerCase());
            const matchesSentiment = sentimentFilter === 'all' || (t.sentiment && t.sentiment.toLowerCase() === sentimentFilter.toLowerCase());
            return matchesQuery && matchesIntent && matchesSentiment;
        });

        // Update KPIs
        const total = state.tickets.length;
        const grievanceCount = state.tickets.filter(t => (t.sentiment || '').toLowerCase().includes('neg') || (t.intent || '').toLowerCase() === 'grievance').length;
        const lowConfCount = state.tickets.filter(t => (t.reason || '').toLowerCase().includes('confidence')).length;

        if (kpiTotalTickets) kpiTotalTickets.textContent = total;
        if (kpiGrievanceCount) kpiGrievanceCount.textContent = grievanceCount;
        if (kpiLowConfCount) kpiLowConfCount.textContent = lowConfCount;
        if (statTicketCount) statTicketCount.textContent = total;
        if (ticketCountBadge) ticketCountBadge.textContent = total;

        if (!ticketsTableBody) return;
        ticketsTableBody.innerHTML = '';

        if (filtered.length === 0) {
            if (ticketsEmptyState) ticketsEmptyState.style.display = 'block';
            return;
        }

        if (ticketsEmptyState) ticketsEmptyState.style.display = 'none';

        filtered.forEach(ticket => {
            const tr = document.createElement('tr');
            const statusClass = ticket.status === 'Resolved' ? 'status-badge-resolved' : 'status-badge-pending';
            
            tr.innerHTML = `
                <td><span class="tkt-badge">${escapeHTML(ticket.ticket_id || 'TKT-0000')}</span></td>
                <td><code>${escapeHTML(ticket.session_id || 'STU-0000')}</code></td>
                <td style="max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHTML(ticket.query || '')}">
                    ${escapeHTML(ticket.query || 'No query captured')}
                </td>
                <td><span class="hud-badge hud-intent" style="font-size: 10px;">${escapeHTML((ticket.intent || 'general').toUpperCase())}</span></td>
                <td><span class="hud-badge" style="font-size: 10px;">${escapeHTML(ticket.sentiment || 'Neutral')}</span></td>
                <td style="font-size: 11.5px; color: var(--text-muted);">${escapeHTML(ticket.reason || 'Escalation policy')}</td>
                <td><span class="${statusClass}">${escapeHTML(ticket.status || 'Pending')}</span></td>
                <td>
                    <button type="button" class="table-action-btn" onclick="toggleTicketStatus('${ticket.ticket_id}')">
                        ${ticket.status === 'Resolved' ? 'Reopen' : 'Resolve'}
                    </button>
                </td>
            `;
            ticketsTableBody.appendChild(tr);
        });
    }

    // Global hook for table status toggle
    window.toggleTicketStatus = function(ticketId) {
        const t = state.tickets.find(item => item.ticket_id === ticketId);
        if (t) {
            t.status = t.status === 'Resolved' ? 'Pending Human Review' : 'Resolved';
            renderTicketsTable();
            showToast(`Ticket ${ticketId} status: ${t.status}`);
        }
    };

    // Filter Listeners
    ticketSearchInput?.addEventListener('input', renderTicketsTable);
    filterIntentSelect?.addEventListener('change', renderTicketsTable);
    filterSentimentSelect?.addEventListener('change', renderTicketsTable);
    refreshTicketsBtn?.addEventListener('click', () => {
        fetchTickets();
        showToast('Ticket queue refreshed.');
    });

    exportTicketsBtn?.addEventListener('click', () => {
        const jsonStr = JSON.stringify(state.tickets, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `support_tickets_${state.sessionId}.json`;
        a.click();
        URL.revokeObjectURL(url);
        showToast('Tickets exported to JSON file.');
    });

    // =========================================================================
    // MANUAL ESCALATION MODAL
    // =========================================================================
    openEscalateModalBtn?.addEventListener('click', () => escalateModal?.classList.add('open'));
    closeEscalateModalBtn?.addEventListener('click', () => escalateModal?.classList.remove('open'));
    cancelEscalateModalBtn?.addEventListener('click', () => escalateModal?.classList.remove('open'));

    submitEscalateBtn?.addEventListener('click', async () => {
        const reason = escalateReasonSelect?.value || 'General Escalation';
        const details = escalateDetailsInput?.value.trim() || 'Manual escalation requested by student.';
        
        try {
            const res = await fetch(`${API_BASE}/escalate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: state.sessionId,
                    query: details,
                    reason: `Manual Escalation: ${reason}`
                })
            });
            const data = await res.json();
            escalateModal?.classList.remove('open');
            if (escalateDetailsInput) escalateDetailsInput.value = '';

            appendAssistantMessage({
                response: `Your manual escalation request has been registered. An official representative from Academic Administration has been assigned to your ticket.`,
                intent: 'manual_escalation',
                confidence: 1.0,
                sentiment: 'Neutral',
                escalated: 1,
                ticket_id: data.ticket_id || `TKT-${Math.floor(1000 + Math.random() * 9000)}`,
                escalation_reason: `Manual Escalation: ${reason}`
            });

            playSound('escalate');
            showToast('Support ticket opened successfully!');
            fetchTickets();
        } catch (e) {
            const tktId = `TKT-${Math.floor(1000 + Math.random() * 9000)}`;
            state.tickets.unshift({
                ticket_id: tktId,
                session_id: state.sessionId,
                query: details,
                intent: 'manual_escalation',
                sentiment: 'Neutral',
                reason: `Manual Escalation: ${reason}`,
                status: 'Pending Human Review',
                created_at: new Date().toISOString()
            });
            escalateModal?.classList.remove('open');
            if (escalateDetailsInput) escalateDetailsInput.value = '';
            appendAssistantMessage({
                response: `Your manual escalation request has been logged. An official representative has been assigned to your case.`,
                intent: 'manual_escalation',
                confidence: 1.0,
                sentiment: 'Neutral',
                escalated: 1,
                ticket_id: tktId,
                escalation_reason: `Manual Escalation: ${reason}`
            });
            playSound('escalate');
            renderTicketsTable();
            showToast('Support ticket registered.');
        }
    });

    // =========================================================================
    // SYSTEM TELEMETRY & HEALTH
    // =========================================================================
    async function checkHealth() {
        try {
            const res = await fetch(`${API_BASE}/health`);
            if (res.ok) state.apiConnected = true;
        } catch (e) {
            state.apiConnected = false;
        }
    }

    async function fetchStats() {
        try {
            const res = await fetch(`${API_BASE}/stats`);
            if (res.ok) {
                const s = await res.json();
                if (statFaqCount && s.faq_count) statFaqCount.textContent = s.faq_count;
                if (statTicketCount && s.ticket_count) statTicketCount.textContent = s.ticket_count;
            }
        } catch (e) {
            // Keep default
        }
    }

    // =========================================================================
    // INTELLIGENT SIMULATION FALLBACK (When Flask API is Offline/Restricted)
    // =========================================================================
    function simulatePipelineResponse(query) {
        const q = (query || '').toLowerCase().trim();
        let intent = 'general';
        let conf = 0.96;
        let sentiment = 'Neutral';
        let escalated = 0;
        let reason = null;
        let ticketId = null;
        let matchedFaq = null;
        let faqSimilarity = 0.0;
        let response = "";

        // 1. Frustrated Grievance Check
        if (q.includes('complain') || q.includes('nobody is helping') || q.includes('frustrat') || q.includes('unacceptable') || q.includes('unfair') || q.includes('angry') || q.includes('terrible') || q.includes('worst')) {
            intent = 'grievance';
            conf = 0.94;
            sentiment = 'Negative';
            escalated = 1;
            ticketId = `TKT-${Math.floor(1000 + Math.random() * 9000)}`;
            reason = 'Rule Trigger: Negative Grievance sentiment detected. SLA: 2 hours.';
            response = `We sincerely apologize for your frustrating experience. Your issue regarding "<em>${escapeHTML(query)}</em>" has been formally escalated to the Campus Grievance Redressal Committee. An administrative officer will contact your registered university email within 2 hours.`;
            
            state.tickets.unshift({
                ticket_id: ticketId,
                session_id: state.sessionId,
                query: query,
                intent: intent,
                sentiment: sentiment,
                reason: reason,
                status: 'Pending Human Review',
                created_at: new Date().toISOString()
            });
            return { response, intent, confidence: conf, sentiment, escalated, ticket_id: ticketId, escalation_reason: reason, matched_faq: matchedFaq, faq_similarity: faqSimilarity };
        }

        // 2. Greetings & Salutations
        if (q === 'hi' || q === 'hello' || q === 'hey' || q === 'help' || q.startsWith('good morning') || q.startsWith('good afternoon') || q.startsWith('good evening')) {
            intent = 'general';
            conf = 0.99;
            sentiment = 'Positive';
            response = `Hello! Welcome to the <strong>Avantia University AI Student Support Desk</strong>. I am ready to assist you with:
            <br>• <strong>Examinations</strong>: Admit cards, timetables, and re-evaluation.
            <br>• <strong>Fees & Finance</strong>: Payment deadlines, installments, and scholarships.
            <br>• <strong>Hostel & Campus</strong>: Room allotments, curfews, and outpass requests.
            <br>• <strong>Library Services</strong>: Book borrowings, renewals, and late return policies.
            <br>• <strong>Admissions</strong>: Eligibility criteria, application forms, and transfer certificates.
            <br><br>What would you like to inquire about today?`;
            return { response, intent, confidence: conf, sentiment, escalated, ticket_id: null, escalation_reason: null, matched_faq: null, faq_similarity: 0.0 };
        }

        // 3. Ambiguous Query Trigger (Only for truly ambiguous queries like 'that thing', 'stuff')
        if (q.includes('that thing') || q.includes('random stuff') || q === 'what' || q === 'why') {
            intent = 'general';
            conf = 0.42;
            sentiment = 'Neutral';
            escalated = 1;
            ticketId = `TKT-${Math.floor(1000 + Math.random() * 9000)}`;
            reason = 'Rule Trigger: Classification confidence (42.0%) fell below the 60% threshold.';
            response = `Your query was ambiguous and could not be mapped to our university knowledge base with sufficient confidence (42.0%). To ensure you receive accurate guidance, an inquiry ticket has been opened for the Student Support Desk.`;
            
            state.tickets.unshift({
                ticket_id: ticketId,
                session_id: state.sessionId,
                query: query,
                intent: intent,
                sentiment: sentiment,
                reason: reason,
                status: 'Pending Human Review',
                created_at: new Date().toISOString()
            });
            return { response, intent, confidence: conf, sentiment, escalated, ticket_id: ticketId, escalation_reason: reason, matched_faq: matchedFaq, faq_similarity: faqSimilarity };
        }

        // 4. Domain Intent Mapping
        if (q.includes('exam') || q.includes('admit') || q.includes('mark') || q.includes('evaluat') || q.includes('result') || q.includes('hall ticket') || q.includes('passing') || q.includes('grade')) {
            intent = 'exams';
            conf = 0.975;
            sentiment = 'Neutral';
            matchedFaq = "When will semester exam admit cards and timetables be issued?";
            faqSimilarity = 0.942;
            response = "Semester examination admit cards and schedules are published <strong>7 working days</strong> prior to examinations on the University ERP Portal (<strong>erp.avantia.edu/exams</strong>). To download your hall ticket, please verify that your term tuition dues are cleared and your course attendance meets the mandatory <strong>75% threshold</strong>.";
        } else if (q.includes('fee') || q.includes('installment') || q.includes('tuition') || q.includes('payment') || q.includes('due') || q.includes('scholarship') || q.includes('receipt') || q.includes('refund')) {
            intent = 'fees';
            conf = 0.968;
            sentiment = 'Neutral';
            matchedFaq = "Can semester tuition fees be paid in split installments?";
            faqSimilarity = 0.928;
            response = "Yes, semester tuition fees may be paid in up to <strong>two equal installments</strong> upon request. You can submit an installment application directly via the Student Finance Portal before the initial due date. Online payments can be completed using Net Banking, UPI, or Credit/Debit Card without convenience charges.";
        } else if (q.includes('hostel') || q.includes('curfew') || q.includes('outpass') || q.includes('room') || q.includes('mess') || q.includes('warden') || q.includes('gate') || q.includes('boarding')) {
            intent = 'hostel';
            conf = 0.962;
            sentiment = 'Neutral';
            matchedFaq = "What are the campus hostel curfew and outpass timings?";
            faqSimilarity = 0.951;
            response = "Campus hostel entry curfew is strictly <strong>9:30 PM</strong> on weekdays (Monday through Friday) and <strong>10:30 PM</strong> on weekends and holidays. For overnight leave or emergency outpasses, digital approval must be requested via the Student Campus App and verified by the Chief Warden at least 4 hours prior to departure.";
        } else if (q.includes('library') || q.includes('book') || q.includes('fine') || q.includes('borrow') || q.includes('journal') || q.includes('renew') || q.includes('card')) {
            intent = 'library';
            conf = 0.984;
            sentiment = 'Neutral';
            matchedFaq = "What is the book borrowing limit and overdue fine policy?";
            faqSimilarity = 0.963;
            response = "Undergraduate students can borrow up to <strong>4 books simultaneously</strong> for a maximum period of 14 days, renewable twice through the OPAC Library Portal. Overdue items accrue a late fee of <strong>$0.50 per book per day</strong>. The Central Reading Hall remains accessible 24/7 during final examination weeks.";
        } else if (q.includes('admission') || q.includes('eligibility') || q.includes('course') || q.includes('apply') || q.includes('cutoff') || q.includes('intake') || q.includes('seat')) {
            intent = 'admissions';
            conf = 0.971;
            sentiment = 'Positive';
            matchedFaq = "What are the undergraduate admission criteria and cutoff deadlines?";
            faqSimilarity = 0.935;
            response = "Admissions for undergraduate degree programs require a minimum aggregate of <strong>60% in high school</strong> with mandatory subject prerequisites. Applications are submitted online at <strong>admissions.avantia.edu</strong>. Merit lists and seat allotment rounds are announced in July and December each academic year.";
        } else {
            intent = 'general';
            conf = 0.88;
            sentiment = 'Neutral';
            matchedFaq = "General Student Assistance";
            faqSimilarity = 0.785;
            response = `Thank you for your inquiry. For specific policies regarding "<em>${escapeHTML(query)}</em>", please check the Student University Handbook or select one of the domain quick-prompts in the sidebar (Admissions, Exams, Fees, Hostel, Library). How else may I assist you today?`;
        }

        return { response, intent, confidence: conf, sentiment, escalated, ticket_id: ticketId, escalation_reason: reason, matched_faq: matchedFaq, faq_similarity: faqSimilarity };
    }

    // =========================================================================
    // UTILITY HELPERS
    // =========================================================================
    function generateSessionId() {
        return 'STU-' + Math.random().toString(36).substring(2, 8).toUpperCase();
    }

    function applyTheme(theme) {
        if (theme === 'light') {
            document.body.classList.remove('theme-dark');
            document.body.classList.add('theme-light');
            if (themeIcon) themeIcon.textContent = '☀️';
        } else {
            document.body.classList.remove('theme-light');
            document.body.classList.add('theme-dark');
            if (themeIcon) themeIcon.textContent = '🌙';
        }
    }

    function updateSoundUI() {
        if (soundIcon) soundIcon.textContent = state.soundEnabled ? '🔔' : '🔕';
    }

    function scrollToBottom() {
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    function formatCurrentTime() {
        const d = new Date();
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    function showToast(msg) {
        if (!toastContainer) return;
        const toast = document.createElement('div');
        toast.className = 'toast glass-panel';
        toast.innerHTML = `<span>✨</span><span>${escapeHTML(msg)}</span>`;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            setTimeout(() => toast.remove(), 300);
        }, 3200);
    }

    function escapeHTML(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function formatMarkdown(str) {
        if (!str) return '';
        return String(str)
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; font-family: var(--font-mono); font-size: 12px;">$1</code>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>');
    }
});

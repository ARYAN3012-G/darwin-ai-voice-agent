/* ==========================================================================
   INTERACTIVE JAVASCRIPT & THREE.JS ANIMATION ENGINE — DARWIN CONTROL CENTER
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initThreeJSBackground();
    initTabNavigation();
    initQ1VoiceAgent();
    initQ2KnowledgeBase();
    initQ3Multilingual();
    initQ4LiveNudgesWS();
});

// Live Clock in Header
function initClock() {
    const clockEl = document.getElementById('live-clock');
    function updateClock() {
        const now = new Date();
        clockEl.textContent = now.toTimeString().split(' ')[0];
    }
    updateClock();
    setInterval(updateClock, 1000);
}

// ---------------------------------------------------------------------------
// Three.js Ambient Particle Background
// ---------------------------------------------------------------------------
function initThreeJSBackground() {
    const canvas = document.getElementById('bg-canvas');
    if (!canvas || typeof THREE === 'undefined') return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });

    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Particle Constellation Geometry
    const particleCount = 120;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const velocities = [];

    for (let i = 0; i < particleCount * 3; i += 3) {
        positions[i] = (Math.random() - 0.5) * 15;
        positions[i + 1] = (Math.random() - 0.5) * 15;
        positions[i + 2] = (Math.random() - 0.5) * 15;

        velocities.push({
            x: (Math.random() - 0.5) * 0.005,
            y: (Math.random() - 0.5) * 0.005,
            z: (Math.random() - 0.5) * 0.005,
        });
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    // Glowing Particle Material
    const material = new THREE.PointsMaterial({
        color: 0x00f2fe,
        size: 0.08,
        transparent: true,
        opacity: 0.7,
        blending: THREE.AdditiveBlending
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    camera.position.z = 8;

    // Animation Loop
    function animate() {
        requestAnimationFrame(animate);

        const posAttr = particles.geometry.attributes.position;
        for (let i = 0; i < particleCount; i++) {
            posAttr.array[i * 3] += velocities[i].x;
            posAttr.array[i * 3 + 1] += velocities[i].y;
            posAttr.array[i * 3 + 2] += velocities[i].z;

            // Bounce bounds
            if (Math.abs(posAttr.array[i * 3]) > 8) velocities[i].x *= -1;
            if (Math.abs(posAttr.array[i * 3 + 1]) > 8) velocities[i].y *= -1;
            if (Math.abs(posAttr.array[i * 3 + 2]) > 8) velocities[i].z *= -1;
        }

        posAttr.needsUpdate = true;
        particles.rotation.y += 0.001;
        particles.rotation.x += 0.0005;

        renderer.render(scene, camera);
    }

    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
}

// ---------------------------------------------------------------------------
// Tab Navigation Logic
// ---------------------------------------------------------------------------
function initTabNavigation() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-tab');

            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(target).classList.add('active');
        });
    });
}

// ---------------------------------------------------------------------------
// Q1 Voice Agent Simulator Logic
// ---------------------------------------------------------------------------
let q1SessionId = null;

function initQ1VoiceAgent() {
    const newCallBtn = document.getElementById('q1-new-call-btn');
    const sendBtn = document.getElementById('q1-send-btn');
    const userInput = document.getElementById('q1-user-input');

    newCallBtn.addEventListener('click', startQ1Call);
    sendBtn.addEventListener('click', sendQ1Message);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendQ1Message();
    });

    startQ1Call(); // Start call on load
}

async function startQ1Call() {
    try {
        const res = await fetch('/api/q1/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await res.json();
        q1SessionId = data.session_id;

        const chatLog = document.getElementById('q1-chat-log');
        chatLog.innerHTML = `
            <div class="message agent-msg">
                <div class="avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="msg-bubble">${data.opening_message}</div>
            </div>
        `;

        updateQ1Inspector("GREETING", "PENDING", [], "Call started. Waiting for customer input...");
    } catch (err) {
        console.error("Failed to start Q1 call:", err);
    }
}

async function sendQ1Message() {
    const userInput = document.getElementById('q1-user-input');
    const text = userInput.value.trim();
    if (!text || !q1SessionId) return;

    appendChatMessage('q1-chat-log', 'user', text);
    userInput.value = '';

    try {
        const res = await fetch('/api/q1/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: q1SessionId, user_input: text })
        });
        const data = await res.json();

        appendChatMessage('q1-chat-log', 'agent', data.response);
        updateQ1Inspector(data.state, data.outcome, data.citations, data.lead_summary);
    } catch (err) {
        console.error("Q1 Chat Error:", err);
    }
}

function updateQ1Inspector(state, outcome, citations, summary) {
    document.getElementById('q1-state-badge').textContent = (state || 'UNKNOWN').toUpperCase();
    
    const outcomeEl = document.getElementById('q1-outcome-badge');
    outcomeEl.textContent = (outcome || 'PENDING').toUpperCase();
    outcomeEl.className = `outcome-badge ${outcome || 'pending'}`;

    const citationsBox = document.getElementById('q1-citations-list');
    if (citations && citations.length > 0) {
        citationsBox.innerHTML = citations.map(c => `<div><i class="fa-solid fa-book-bookmark text-green"></i> ${c}</div>`).join('');
    } else {
        citationsBox.innerHTML = '<span class="text-muted">No citations requested for current turn.</span>';
    }

    document.getElementById('q1-lead-summary').textContent = summary || "No lead data recorded yet.";
}

function appendChatMessage(containerId, role, text) {
    const container = document.getElementById(containerId);
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}-msg`;

    const icon = role === 'agent' ? '<i class="fa-solid fa-robot"></i>' : '<i class="fa-solid fa-user"></i>';
    msgDiv.innerHTML = `
        <div class="avatar">${icon}</div>
        <div class="msg-bubble">${text}</div>
    `;

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

// ---------------------------------------------------------------------------
// Q2 Knowledge Base Inspector Logic
// ---------------------------------------------------------------------------
function initQ2KnowledgeBase() {
    const searchBtn = document.getElementById('q2-search-btn');
    const searchInput = document.getElementById('q2-search-input');
    const cleanBtn = document.getElementById('q2-clean-btn');

    searchBtn.addEventListener('click', runQ2Search);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') runQ2Search();
    });

    document.querySelectorAll('.chip-btn').forEach(chip => {
        chip.addEventListener('click', () => {
            searchInput.value = chip.getAttribute('data-query');
            runQ2Search();
        });
    });

    cleanBtn.addEventListener('click', runQ2Cleaner);
}

async function runQ2Search() {
    const query = document.getElementById('q2-search-input').value.trim();
    if (!query) return;

    const container = document.getElementById('q2-results-container');
    container.innerHTML = '<div class="text-muted">Searching Hybrid Index (BM25 + Dense RRF)...</div>';

    try {
        const res = await fetch('/api/q2/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, top_k: 5 })
        });
        const data = await res.json();

        if (!data.results || data.results.length === 0) {
            container.innerHTML = '<div class="text-muted">No results found for query.</div>';
            return;
        }

        container.innerHTML = data.results.map(r => `
            <div class="result-card">
                <div class="result-header">
                    <span class="result-title">[#${r.rank}] ${r.title}</span>
                    <div class="score-pills">
                        <span class="score-pill">BM25: ${r.bm25_score}</span>
                        <span class="score-pill">Dense: ${r.dense_score}</span>
                        <span class="score-pill highlight-blue">RRF: ${r.rrf_score}</span>
                    </div>
                </div>
                <div class="snippet-text">${r.content_snippet}</div>
                <div class="text-muted" style="font-size: 11px;"><i class="fa-solid fa-quote-left"></i> ${r.citation}</div>
            </div>
        `).join('');
    } catch (err) {
        console.error("Q2 Search Error:", err);
    }
}

async function runQ2Cleaner() {
    const rawText = document.getElementById('q2-clean-input').value;
    try {
        const res = await fetch('/api/q2/clean', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: rawText })
        });
        const data = await res.json();

        document.getElementById('q2-clean-metrics').style.display = 'flex';
        document.getElementById('q2-pii-count').textContent = data.pii_masked_count;
        document.getElementById('q2-header-status').textContent = data.headers_footers_removed ? 'Yes' : 'No';

        document.getElementById('q2-clean-output').textContent = data.cleaned_text;
    } catch (err) {
        console.error("Q2 Cleaner Error:", err);
    }
}

// ---------------------------------------------------------------------------
// Q3 Multilingual Bots & Loan Calculator Logic
// ---------------------------------------------------------------------------
let activeBotLang = 'ph'; // 'ph' or 'id'

function initQ3Multilingual() {
    const phBtn = document.getElementById('ph-bot-btn');
    const idBtn = document.getElementById('id-bot-btn');
    const sendBtn = document.getElementById('q3-send-btn');
    const userInput = document.getElementById('q3-user-input');
    const calcBtn = document.getElementById('calc-run-btn');

    phBtn.addEventListener('click', () => setBotLang('ph'));
    idBtn.addEventListener('click', () => setBotLang('id'));

    sendBtn.addEventListener('click', sendQ3Message);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendQ3Message();
    });

    calcBtn.addEventListener('click', runLoanCalculation);
}

function setBotLang(lang) {
    activeBotLang = lang;
    document.getElementById('ph-bot-btn').classList.toggle('active', lang === 'ph');
    document.getElementById('id-bot-btn').classList.toggle('active', lang === 'id');

    const welcomeMsg = lang === 'ph'
        ? "Magandang araw po! Salamat sa inyong pagtawag. Nandito po ako para tulungan kayo sa aming life insurance at health insurance. Paano ko po kayo matutulungan ngayon?"
        : "Halo! Makasih udah hubungin kami. Bisa saya bantu soal pinjaman atau kredit yang Bapak/Ibu butuhkan?";

    document.getElementById('q3-chat-log').innerHTML = `
        <div class="message agent-msg">
            <div class="avatar"><i class="fa-solid fa-robot"></i></div>
            <div class="msg-bubble">${welcomeMsg}</div>
        </div>
    `;
}

async function sendQ3Message() {
    const userInput = document.getElementById('q3-user-input');
    const text = userInput.value.trim();
    if (!text) return;

    appendChatMessage('q3-chat-log', 'user', text);
    userInput.value = '';

    const endpoint = activeBotLang === 'ph' ? '/api/q3/ph/chat' : '/api/q3/id/chat';

    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_input: text })
        });
        const data = await res.json();

        appendChatMessage('q3-chat-log', 'agent', data.response);

        // Update Quality Breakdown
        const ratingEl = document.getElementById('q3-quality-rating');
        ratingEl.textContent = data.quality_rating;
        ratingEl.className = `quality-badge ${(data.quality_rating || 'EXCELLENT').toLowerCase()}`;

        document.getElementById('q3-quality-score').textContent = data.quality_score.toFixed(2);
        document.getElementById('q3-local-terms').textContent = data.local_terms_found.join(', ') || 'None';
        document.getElementById('q3-respect-markers').textContent = data.respect_markers_found.join(', ') || 'None';
        document.getElementById('q3-quality-note').textContent = data.notes;
    } catch (err) {
        console.error("Q3 Bot Error:", err);
    }
}

async function runLoanCalculation() {
    const p = parseFloat(document.getElementById('calc-principal').value);
    const r = parseFloat(document.getElementById('calc-rate').value);
    const t = parseInt(document.getElementById('calc-tenor').value);

    try {
        const res = await fetch('/api/q3/calculate-loan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ principal_idr: p, interest_rate_pa: r, tenor_months: t })
        });
        const data = await res.json();

        document.getElementById('calc-results').style.display = 'flex';
        document.getElementById('calc-cicilan').textContent = `Rp ${Math.round(data.cicilan_per_bulan).toLocaleString()}`;
        document.getElementById('calc-total').textContent = `Rp ${Math.round(data.total_pembayaran).toLocaleString()}`;
        document.getElementById('calc-bunga').textContent = `Rp ${Math.round(data.total_bunga).toLocaleString()}`;
    } catch (err) {
        console.error("Loan Calc Error:", err);
    }
}

// ---------------------------------------------------------------------------
// Q4 Live Nudges & Latency Telemetry WebSocket Logic
// ---------------------------------------------------------------------------
let ws = null;

function initQ4LiveNudgesWS() {
    const wsBtn = document.getElementById('ws-start-btn');
    wsBtn.addEventListener('click', toggleWSStream);
}

function toggleWSStream() {
    const wsBtn = document.getElementById('ws-start-btn');

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
        wsBtn.innerHTML = '<i class="fa-solid fa-play"></i> Start Stream Simulation';
        wsBtn.className = 'btn btn-success';
        return;
    }

    const feed = document.getElementById('q4-nudge-feed');
    feed.innerHTML = '';

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/nudges/sim_${Date.now()}`;

    ws = new WebSocket(wsUrl);

    wsBtn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop Stream';
    wsBtn.className = 'btn btn-secondary';

    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === 'TRANSCRIPT') {
            const div = document.createElement('div');
            div.className = 'text-muted';
            div.style.fontSize = '12px';
            div.innerHTML = `<strong>[${msg.speaker}]</strong> ${msg.text} <span style="font-size:10px;">(${msg.latency_ms.toFixed(1)}ms)</span>`;
            feed.appendChild(div);
            feed.scrollTop = feed.scrollHeight;
        } else if (msg.type === 'NUDGE') {
            const card = document.createElement('div');
            card.className = `nudge-card ${msg.priority}`;
            card.innerHTML = `
                <div class="nudge-header">
                    <span>${msg.title}</span>
                    <span>${msg.priority}</span>
                </div>
                <div class="nudge-action">${msg.action_text}</div>
            `;
            feed.appendChild(card);
            feed.scrollTop = feed.scrollHeight;
        } else if (msg.type === 'TELEMETRY') {
            updateTelemetry(msg);
        }
    };

    ws.onclose = () => {
        wsBtn.innerHTML = '<i class="fa-solid fa-play"></i> Start Stream Simulation';
        wsBtn.className = 'btn btn-success';
    };
}

function updateTelemetry(msg) {
    const overallBadge = document.getElementById('overall-sla-badge');
    overallBadge.textContent = msg.overall_sla_pass ? 'ALL SLA TARGETS MET' : 'SLA BREACH DETECTED';
    overallBadge.className = `sla-badge ${msg.overall_sla_pass ? 'pass' : 'fail'}`;

    const stages = msg.stages;

    if (stages.ASR) {
        document.getElementById('asr-p50').textContent = `${stages.ASR.p50.toFixed(1)}ms`;
        document.getElementById('asr-p95').textContent = `${stages.ASR.p95.toFixed(1)}ms`;
    }
    if (stages.SIGNAL_EXTRACTION) {
        document.getElementById('sig-p50').textContent = `${stages.SIGNAL_EXTRACTION.p50.toFixed(1)}ms`;
        document.getElementById('sig-p95').textContent = `${stages.SIGNAL_EXTRACTION.p95.toFixed(1)}ms`;
    }
    if (stages.NUDGE_GENERATION) {
        document.getElementById('nudge-p50').textContent = `${stages.NUDGE_GENERATION.p50.toFixed(1)}ms`;
        document.getElementById('nudge-p95').textContent = `${stages.NUDGE_GENERATION.p95.toFixed(1)}ms`;
    }
    if (stages.END_TO_END) {
        document.getElementById('e2e-p50').textContent = `${stages.END_TO_END.p50.toFixed(1)}ms`;
        document.getElementById('e2e-p95').textContent = `${stages.END_TO_END.p95.toFixed(1)}ms`;
    }
}

# AI Voice Agent Assessment System — DARWIN Control Center

A production-grade, modular AI Voice Agent System addressing all 4 Core Questions of the assessment with zero-hallucination RAG, deterministic state machine qualification, native multilingual bots, live streaming WebSocket nudges, and an interactive **Three.js Black Gradient Control Center**.

---

## 🌐 Live Deployed Application

> 🔗 **Live Website URL**: **[https://darwin-ai-voice-agent.onrender.com](https://darwin-ai-voice-agent.onrender.com)**  
> ⚡ *Hosted live on Render.com with FastAPI, WebSockets & Three.js 3D Background.*

---

## 📹 Video Demonstration & Walkthrough

> **[INSERT YOUR LOOM / YOUTUBE VIDEO LINK HERE]**

### Suggested Video Recording Outline (3–5 minutes):
1. **Introduction & System Overview**: Show the live Three.js Black Gradient Dashboard.
2. **Q1 Voice Agent**: Demonstrate Health Insurance & Business Loan qualification flows, state transitions, grounded citations, and manager escalation.
3. **Q2 Knowledge Base**: Demonstrate BM25 + Dense RRF hybrid search rankings and the PII Cleaner/Masker.
4. **Q3 Multilingual Bots**: Demonstrate Taglish (PH) insurance bot, Bahasa (ID) loan bot, quality scoring, and the Indonesian Simulasi Kredit calculator.
5. **Q4 Live Nudges & SLA**: Click "Start Stream Simulation", show WebSocket audio streaming, real-time priority Nudge Cards, and P50/P95 latency SLA benchmarks.

---

## 📋 Comprehensive Feature Audit vs. Assessment Requirements

| Requirement Module | PDF Specification | Implementation Details | Status |
|---|---|---|---|
| **Q1: Grounded Voice Agent** | Dual use case (Insurance & Loans), RAG grounding, state machine, fallback & escalation | State machine in `q1_voice_agent/qualification_flow.py`, RAG brain in `q1_voice_agent/agent_brain.py` | ✅ 100% Complete |
| **Q2: Knowledge Base** | Header/footer stripping, Jaccard dedup, PII masking, BM25+Dense RRF hybrid search | `DocumentCleaner` in `q2_knowledge_base/cleaner.py`, `HybridRetriever` in `q2_knowledge_base/retriever.py` | ✅ 100% Complete |
| **Q3: Multilingual Bots** | Taglish (PH) & Bahasa (ID) bots, local terminology, respect markers, quality scoring, loan calc | `PhilippinesInsuranceBot` in `q3_multilingual/philippines_bot.py`, `IndonesiaLoanBot` in `q3_multilingual/indonesia_bot.py` | ✅ 100% Complete |
| **Q4: Live Nudges & SLA** | Audio chunk stream, signal extraction, nudge cooldowns, P50/P95 latency monitoring | WebSocket streaming in `web/app.py`, `NudgeEngine` in `q4_live_nudges/nudge_engine.py` | ✅ 100% Complete |
| **Web Dashboard** | Interactive UI with rich aesthetics, real-time WebSockets, and state inspection | FastAPI + WebSockets (`web/app.py`), Three.js Canvas background (`web/static/app.js`) | ✅ 100% Complete |

---

## 📁 Repository Structure

```
ARG_DARWIN/
├── requirements.txt            # Python package dependencies
├── .gitignore                  # Git ignore rules
├── README.md                   # Complete system documentation
│
├── q1_voice_agent/             # Q1: Knowledge-grounded voice agent
│   ├── qualification_flow.py   # Lead qualification state machine & handlers
│   ├── agent_brain.py          # Zero-hallucination RAG brain
│   └── run_test_calls.py       # Standalone test suite for Q1
│
├── q2_knowledge_base/          # Q2: Production-ready knowledge base
│   ├── schema.py               # Pydantic v2 document & PII schemas
│   ├── cleaner.py              # Header/footer stripping & PII masker
│   ├── knowledge_data.py       # Seed knowledge base documents (PH & ID)
│   ├── vector_store.py         # TF-IDF dense vector store
│   ├── retriever.py            # Hybrid BM25 + Dense RRF retriever
│   └── run_retrieval_tests.py   # Standalone retrieval & cleaner test suite
│
├── q3_multilingual/            # Q3: Native-language voice bots
│   ├── localization_engine.py  # Code-switching quality scorer & lexicons
│   ├── philippines_bot.py      # Taglish life insurance bot (PH)
│   ├── indonesia_bot.py        # Bahasa Indonesia consumer loan bot (ID)
│   └── run_multilingual_tests.py # Standalone test suite for Q3
│
├── q4_live_nudges/             # Q4: Live insights & real-time nudges
│   ├── stream_processor.py     # Streaming audio pipeline & simulated ASR
│   ├── signal_extractor.py     # Pattern & speaker-aware signal extractor
│   ├── nudge_engine.py         # Priority nudges, cooldowns & suppression
│   ├── latency_monitor.py      # P50/P95 latency telemetry SLA monitor
│   └── run_nudge_tests.py      # Standalone nudge simulation test suite
│
└── web/                        # Web Dashboard (FastAPI + WebSockets)
    ├── app.py                  # FastAPI REST + WebSocket application
    ├── templates/index.html    # Dashboard HTML template
    └── static/
        ├── styles.css          # Black gradient glassmorphism design system
        └── app.js              # Three.js 3D background & WebSocket client
```

---

## 🚀 Local Setup & Installation

### 1. Clone & Install Dependencies
```bash
git clone <YOUR-GITHUB-REPO-URL>
cd ARG_DARWIN

# Create virtual environment (optional)
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Run Module Terminal Verification Suites
```bash
# Verify Q1 Voice Agent
python q1_voice_agent/run_test_calls.py

# Verify Q2 Knowledge Base
python q2_knowledge_base/run_retrieval_tests.py

# Verify Q3 Multilingual Bots
python q3_multilingual/run_multilingual_tests.py

# Verify Q4 Live Nudges & Telemetry
python q4_live_nudges/run_nudge_tests.py
```

### 3. Launch the Web Dashboard
```bash
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn web.app:app --port 8000 --reload
```
Then open your browser to **http://localhost:8000**.

---

## 🌐 Deploying to Production (Render / Railway / Docker)

### Option A: Deploy on Render.com (Recommended)
1. Push your repository to GitHub.
2. Log into [Render.com](https://render.com) and click **New +** $\rightarrow$ **Web Service**.
3. Connect your GitHub repository.
4. Set the following settings:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m uvicorn web.app:app --host 0.0.0.0 --port $PORT`
5. Click **Deploy Web Service**!

### Option B: Deploy with Docker
Build and run the container locally or on any cloud server:

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 📤 Pushing to GitHub

To push your repository to GitHub:

```bash
git init
git add .
git commit -m "Initial commit: Production AI Voice Agent System with Web Dashboard"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

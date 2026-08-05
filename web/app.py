"""
Web Dashboard Application for AI Voice Agent Assessment System
================================================================
FastAPI server hosting REST APIs and WebSocket endpoints for:
- Q1: Knowledge-grounded AI Voice Agent simulation & state machine
- Q2: Hybrid BM25 + Dense RRF Knowledge Base search & PII cleaner
- Q3: Multilingual Taglish (PH) & Bahasa Indonesia (ID) bots + Loan calculator
- Q4: Live real-time WebSocket nudge streaming & Latency SLA telemetry
"""

import asyncio
import os
import sys
import uuid
import time
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

# Ensure parent directory is in python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from q1_voice_agent.agent_brain import VoiceAgentBrain
from q1_voice_agent.qualification_flow import QualificationFlow
from q2_knowledge_base.cleaner import DocumentCleaner
from q2_knowledge_base.retriever import HybridRetriever
from q3_multilingual.indonesia_bot import IndonesiaLoanBot
from q3_multilingual.localization_engine import LocalizationEngine
from q3_multilingual.philippines_bot import PhilippinesInsuranceBot
from q4_live_nudges.latency_monitor import LatencyMonitor
from q4_live_nudges.nudge_engine import NudgeEngine
from q4_live_nudges.signal_extractor import SignalExtractor
from q4_live_nudges.stream_processor import StreamProcessor

app = FastAPI(title="AI Voice Agent Control Center", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup template & static files
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ---------------------------------------------------------------------------
# Global Singletons — built once at startup
# ---------------------------------------------------------------------------
retriever = HybridRetriever()
retriever.build()
brain = VoiceAgentBrain(retriever=retriever)
cleaner = DocumentCleaner()
loc_engine = LocalizationEngine()

# Per-request bot instances (stateful per session — stored in dict)
_ph_bots: Dict[str, PhilippinesInsuranceBot] = {}
_id_bots: Dict[str, IndonesiaLoanBot] = {}


def get_ph_bot(session_id: str) -> PhilippinesInsuranceBot:
    if session_id not in _ph_bots:
        _ph_bots[session_id] = PhilippinesInsuranceBot()
    return _ph_bots[session_id]


def get_id_bot(session_id: str) -> IndonesiaLoanBot:
    if session_id not in _id_bots:
        _id_bots[session_id] = IndonesiaLoanBot()
    return _id_bots[session_id]


# ---------------------------------------------------------------------------
# Q1 REST Models & Endpoints
# ---------------------------------------------------------------------------

class Q1StartRequest(BaseModel):
    session_id: Optional[str] = None


class Q1ChatRequest(BaseModel):
    session_id: str
    user_input: str


@app.post("/api/q1/start")
def q1_start(req: Q1StartRequest):
    session_id = req.session_id or str(uuid.uuid4())[:8]
    opening_msg, session = brain.start_call(session_id=session_id)
    return {
        "session_id": session_id,
        "opening_message": opening_msg,
        "state": session.final_state or "greeting",
    }


@app.post("/api/q1/chat")
def q1_chat(req: Q1ChatRequest):
    session = brain.get_session(req.session_id)
    if not session:
        brain.start_call(session_id=req.session_id)

    response = brain.process_turn(req.session_id, req.user_input)
    updated_session = brain.get_session(req.session_id)
    last_turn = updated_session.turns[-1] if updated_session and updated_session.turns else None

    flow: Optional[QualificationFlow] = brain._sessions.get(f"_flow_{req.session_id}")

    return {
        "session_id": req.session_id,
        "response": response,
        "state": updated_session.final_state if updated_session else "unknown",
        "outcome": updated_session.outcome if updated_session else "pending",
        "grounded": last_turn.grounded if last_turn else False,
        "citations": last_turn.citations_used if last_turn else [],
        "lead_summary": flow.lead.to_summary() if flow else "",
    }


# ---------------------------------------------------------------------------
# Q2 REST Models & Endpoints
# ---------------------------------------------------------------------------

class Q2SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class Q2CleanRequest(BaseModel):
    text: str


@app.post("/api/q2/search")
def q2_search(req: Q2SearchRequest):
    report = retriever.search_and_report(query=req.query, top_k=req.top_k)
    return {
        "query": report.query,
        "retrieval_time_ms": report.retrieval_time_ms,
        "verdict": report.verdict,
        "total_indexed": report.total_indexed,
        "results": [
            {
                "rank": r.rank,
                "record_id": r.record_id,
                "title": r.title,
                "summary": r.summary,
                "content_snippet": r.content_snippet,
                "category": r.category,
                "markets": r.markets,
                "bm25_score": r.bm25_score,
                "dense_score": r.dense_score,
                "rrf_score": r.rrf_score,
                "citation": r.citation,
            }
            for r in report.results
        ],
    }


@app.post("/api/q2/clean")
def q2_clean(req: Q2CleanRequest):
    res = cleaner.clean(req.text)
    return {
        "original_length": len(req.text),
        "cleaned_length": len(res.cleaned_text),
        "headers_footers_removed": bool(res.headers_stripped + res.footers_stripped),
        "pii_masked_count": len(res.pii_detections),
        "pii_details": [p.model_dump() for p in res.pii_detections],
        "cleaned_text": res.cleaned_text,
    }


# ---------------------------------------------------------------------------
# Q3 REST Models & Endpoints
# ---------------------------------------------------------------------------

class Q3PHChatRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = "ph_default"


class Q3IDChatRequest(BaseModel):
    user_input: str
    session_id: Optional[str] = "id_default"


class Q3LoanCalcRequest(BaseModel):
    principal_idr: float
    interest_rate_pa: float
    tenor_months: int


@app.post("/api/q3/ph/chat")
def q3_ph_chat(req: Q3PHChatRequest):
    bot = get_ph_bot(req.session_id)
    bot_response = bot.respond(req.user_input)

    # Get quality from localization engine
    lang = loc_engine.detect_language(req.user_input)
    quality = loc_engine.score_code_switch_quality(req.user_input, lang)

    return {
        "response": bot_response,
        "quality_score": quality.score,
        "quality_rating": quality.quality_label(),
        "language_detected": quality.primary_language.value,
        "local_terms_found": quality.local_terms_used,
        "respect_markers_found": quality.respect_markers_detected,
        "notes": quality.notes,
        "state": bot.state.value,
    }


@app.post("/api/q3/id/chat")
def q3_id_chat(req: Q3IDChatRequest):
    bot = get_id_bot(req.session_id)
    bot_response = bot.respond(req.user_input)

    lang = loc_engine.detect_language(req.user_input)
    quality = loc_engine.score_code_switch_quality(req.user_input, lang)

    return {
        "response": bot_response,
        "quality_score": quality.score,
        "quality_rating": quality.quality_label(),
        "language_detected": quality.primary_language.value,
        "local_terms_found": quality.local_terms_used,
        "respect_markers_found": quality.respect_markers_detected,
        "notes": quality.notes,
        "state": bot.state.value,
    }


@app.post("/api/q3/calculate-loan")
def q3_calculate_loan(req: Q3LoanCalcRequest):
    # Use the bot's simulate_loan method which takes (principal_idr, annual_rate_pct, tenor_months)
    bot = IndonesiaLoanBot()
    result_text = bot.simulate_loan(
        principal_idr=req.principal_idr,
        annual_rate_pct=req.interest_rate_pa,
        tenor_months=req.tenor_months,
    )

    # Also compute numeric values for the frontend
    monthly_rate = req.interest_rate_pa / 100 / 12
    if monthly_rate == 0:
        monthly_payment = req.principal_idr / req.tenor_months
    else:
        monthly_payment = (
            req.principal_idr * monthly_rate * (1 + monthly_rate) ** req.tenor_months
        ) / ((1 + monthly_rate) ** req.tenor_months - 1)

    total_payment = monthly_payment * req.tenor_months
    total_interest = total_payment - req.principal_idr

    return {
        "cicilan_per_bulan": round(monthly_payment, 0),
        "total_pembayaran": round(total_payment, 0),
        "total_bunga": round(total_interest, 0),
        "formatted_text": result_text,
    }


# ---------------------------------------------------------------------------
# Q4 WebSocket Streaming (Live Nudges & Latency Telemetry)
# ---------------------------------------------------------------------------

from q4_live_nudges.stream_processor import StreamProcessor, Speaker

CALL_SCRIPT = [
    (Speaker.CUSTOMER, "Hello, I'm calling to inquire about insurance policies for my family."),
    (Speaker.AGENT,    "Hello! Thank you for calling. I'd be happy to help you with our health and life plans."),
    (Speaker.CUSTOMER, "I'm 42 years old, but I have a pre-existing heart condition from 3 years ago."),
    (Speaker.AGENT,    "We offer comprehensive health plans starting at PHP 12,000 per year."),
    (Speaker.CUSTOMER, "What if I get sick during the waiting period? And do I need to pay annually?"),
    (Speaker.AGENT,    "Premium payment can be annual, semi-annual, or monthly."),
    (Speaker.CUSTOMER, "I want to apply for a business loan for my retail store as well."),
    (Speaker.AGENT,    "Great. We offer business loans with coverage up to PHP 10 million."),
    (Speaker.CUSTOMER, "What's the interest rate? And do you have a maternity benefit option?"),
    (Speaker.AGENT,    "The interest rate is 1.5% per month on declining balance."),
    (Speaker.CUSTOMER, "That seems high. I've already contacted a lawyer about my options."),
    (Speaker.AGENT,    "I understand. Let me explain — we offer competitive rates and flexible tenor choices."),
    (Speaker.CUSTOMER, "I want to speak to a supervisor right now. This is unacceptable."),
    (Speaker.AGENT,    "Of course. Before I transfer you, may I also mention we have a family plan?"),
    (Speaker.CUSTOMER, "Please just transfer me. I may sue if this isn't resolved today."),
]


@app.websocket("/ws/nudges/{session_id}")
async def websocket_nudges(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # Build the streaming pipeline
    stream_proc = StreamProcessor(session_id=session_id)
    stream_proc.load_call_script(CALL_SCRIPT)

    signal_ext = SignalExtractor()
    nudge_eng = NudgeEngine(session_id=session_id)
    latency_mon = LatencyMonitor(session_id=session_id)

    try:
        for seg in stream_proc.stream(chunk_count=len(CALL_SCRIPT) * 4):
            await asyncio.sleep(0.8)  # Realistic turn pacing

            # Record ASR latency
            latency_mon.record("ASR", seg.asr_latency_ms)

            speaker_str = seg.speaker.value if hasattr(seg.speaker, 'value') else str(seg.speaker)

            # Emit transcript event
            await websocket.send_json({
                "type": "TRANSCRIPT",
                "segment_id": seg.segment_id,
                "speaker": speaker_str.upper(),
                "text": seg.text,
                "latency_ms": round(seg.asr_latency_ms, 1),
            })

            # Extract signals from this segment
            sig_start = time.perf_counter()
            signals = signal_ext.extract(seg)
            sig_lat = (time.perf_counter() - sig_start) * 1000
            latency_mon.record("SIGNAL_EXTRACTION", sig_lat)

            for sig in signals:
                await websocket.send_json({
                    "type": "SIGNAL",
                    "signal_type": sig.signal_type.value,
                    "confidence": sig.confidence,
                    "extracted_text": sig.matched_phrase,
                })

                # Generate nudge from signal
                n_start = time.perf_counter()
                nudge = nudge_eng.process_signal(sig)
                n_lat = (time.perf_counter() - n_start) * 1000
                latency_mon.record("NUDGE_GENERATION", n_lat)

                if nudge:
                    latency_mon.record("END_TO_END", seg.asr_latency_ms + sig_lat + n_lat)
                    await websocket.send_json({
                        "type": "NUDGE",
                        "nudge_id": nudge.nudge_id,
                        "title": nudge.title,
                        "action_text": nudge.body,
                        "priority": nudge.priority.name,   # e.g. "CRITICAL", "HIGH", "MEDIUM"
                        "trigger_signal": nudge.signal_type.value,
                    })

            # Emit telemetry after each segment
            report = latency_mon.generate_report()
            summary_data = {}
            for stage, stat in report.stages.items():
                summary_data[stage] = {
                    "p50": stat.p50_ms,
                    "p95": stat.p95_ms,
                    "p99": stat.p99_ms,
                    "target_p95": stat.sla_target_ms or 0,
                    "pass": stat.sla_compliant if stat.sla_compliant is not None else True,
                }

            await websocket.send_json({
                "type": "TELEMETRY",
                "overall_sla_pass": report.overall_sla_compliant,
                "stages": summary_data,
            })

    except WebSocketDisconnect:
        print(f"[WS] Client disconnected: {session_id}")
    except Exception as e:
        print(f"[WS] Error in session {session_id}: {e}")
        import traceback
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Dashboard Route
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=True)

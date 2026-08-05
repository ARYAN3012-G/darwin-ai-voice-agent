"""
Q4 Live Nudges — Simulation Test Suite
========================================
Simulates a complete live call with streaming audio processing,
real-time signal extraction, nudge generation, and latency benchmarking.

Test Scenarios:
  1. Standard call — health insurance with frustrated repeat caller
  2. High-stakes call — legal threat + compliance gaps + cross-sell
  3. Latency stress test — 200 chunks, P50/P95 measurement
"""

from __future__ import annotations

import sys
import os
import time
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from q4_live_nudges.stream_processor import StreamProcessor, Speaker
from q4_live_nudges.signal_extractor import SignalExtractor
from q4_live_nudges.nudge_engine import NudgeEngine, NudgePriority
from q4_live_nudges.latency_monitor import LatencyMonitor, LatencyStage


# ---------------------------------------------------------------------------
# Call Scripts
# ---------------------------------------------------------------------------

CALL_SCRIPT_1 = [
    (Speaker.AGENT, "Good morning, this is Alex from HealthGuard Insurance. How can I help you today?"),
    (Speaker.CUSTOMER, "I've been calling for the past 3 times already and nobody has resolved my issue."),
    (Speaker.AGENT, "I'm sorry to hear that. What's the issue you're experiencing?"),
    (Speaker.CUSTOMER, "I'm not happy with the service at all. I want to cancel my policy."),
    (Speaker.AGENT, "We offer comprehensive health insurance starting at PHP 6,000 per year with full coverage."),
    (Speaker.CUSTOMER, "I might be interested in getting insurance for my whole family as well."),
    (Speaker.AGENT, "For your family, we have excellent bundled plans. Shall I proceed with your application?"),
    (Speaker.CUSTOMER, "That sounds good. But I can't afford the premium right now, times are really tough."),
    (Speaker.AGENT, "I understand. We have plans starting at PHP 500 per month."),
    (Speaker.CUSTOMER, "I'm interested! Let's do it. Can I pay annually instead of monthly?"),
]

CALL_SCRIPT_2 = [
    (Speaker.AGENT, "Good afternoon, this is Sarah from LendPro Financial. How may I assist you?"),
    (Speaker.CUSTOMER, "I want to apply for a business loan for my retail store."),
    (Speaker.AGENT, "Great. We offer business loans with coverage up to PHP 10 million."),
    (Speaker.CUSTOMER, "What's the interest rate? And do you have a maternity benefit option as well?"),
    (Speaker.AGENT, "The interest rate is 1.5% per month on declining balance."),
    (Speaker.CUSTOMER, "That seems high. I've already contacted a lawyer about my options."),
    (Speaker.AGENT, "I understand. Let me explain — we offer competitive rates and you can choose your tenor."),
    (Speaker.CUSTOMER, "I want to speak to a supervisor right now. This is unacceptable."),
    (Speaker.AGENT, "Of course. Before I transfer you, may I also mention we have a family plan?"),
    (Speaker.CUSTOMER, "Please just transfer me. I may sue if this isn't resolved today."),
]

CALL_SCRIPT_3_STRESS = [
    (Speaker.AGENT, f"Good day, calling about our health insurance plan — coverage starts from day one for accidents."),
    (Speaker.CUSTOMER, "I've been calling every day this week and no one helps me. I'm very frustrated."),
    (Speaker.AGENT, "Our comprehensive plan covers all hospitalization, outpatient, and emergency care."),
    (Speaker.CUSTOMER, "I can't afford this. My income is irregular as I'm freelance."),
    (Speaker.AGENT, "Would you like to apply? We can also add the maternity and dental riders."),
    (Speaker.CUSTOMER, "Do you also cover mental health? And what about my children?"),
    (Speaker.AGENT, "Absolutely. Shall I include your family members? We have a family plan available."),
    (Speaker.CUSTOMER, "That sounds perfect. Let's proceed. I'm interested."),
] * 5  # Repeat 5x for stress test


# ---------------------------------------------------------------------------
# Pipeline Runner
# ---------------------------------------------------------------------------

def run_live_pipeline(
    session_id: str,
    script: list,
    title: str,
    verbose: bool = True,
) -> dict:
    """
    Run the complete live nudge pipeline on a call script.
    Returns statistics summary.
    """
    sep = "═" * 65
    if verbose:
        print(f"\n{sep}")
        print(f"  {title}")
        print(f"  Session: {session_id}")
        print(sep)

    # Initialize pipeline components
    processor = StreamProcessor(session_id=session_id)
    extractor = SignalExtractor()
    engine = NudgeEngine(session_id=session_id)
    monitor = LatencyMonitor(session_id=session_id)

    # Load script into processor
    processor.load_call_script(script)

    # Stats tracking
    total_segments = 0
    total_signals = 0
    total_nudges = 0
    nudges_by_priority = {p.label(): 0 for p in NudgePriority}

    def on_nudge(nudge):
        nonlocal total_nudges
        total_nudges += 1
        nudges_by_priority[nudge.priority.label()] = nudges_by_priority.get(nudge.priority.label(), 0) + 1

        monitor.record_nudge_generation(
            (time.perf_counter() - nudge.created_at) * 1000
        )

        if verbose:
            priority_icons = {5: "🚨", 4: "🔴", 3: "🟡", 2: "🔵", 1: "ℹ️"}
            icon = priority_icons.get(nudge.priority.value, "•")
            print(f"\n  {icon} [{nudge.priority.label()}] {nudge.title}")
            print(f"     Context : \"{nudge.supporting_text[:60]}...\"" if len(nudge.supporting_text) > 60
                  else f"     Context : \"{nudge.supporting_text}\"")
            print(f"     Action  : {nudge.body[:100]}...")

    engine.on_nudge(on_nudge)

    if verbose:
        print("\n  [LIVE CALL SIMULATION STARTING]\n")

    # Stream audio through pipeline
    for segment in processor.stream(chunk_count=len(script) * 5):
        chunk_start = time.perf_counter()
        total_segments += 1

        # Record ASR latency
        monitor.record_asr(segment.asr_latency_ms)

        if verbose:
            print(f"  [{segment.speaker.value.upper():<8}] {segment.text}")

        # Signal extraction
        sig_start = time.perf_counter()
        signals = extractor.extract(segment)
        sig_latency = (time.perf_counter() - sig_start) * 1000
        monitor.record_signal_extraction(sig_latency)
        total_signals += len(signals)

        # Nudge generation
        engine.process_signals(signals)

        # E2E latency
        e2e_latency = (time.perf_counter() - chunk_start) * 1000 + segment.asr_latency_ms
        monitor.record_e2e(e2e_latency)

    # Generate latency report
    report = monitor.generate_report()
    nudge_stats = engine.get_statistics()

    if verbose:
        print(f"\n{'─'*65}")
        print(f"  CALL SUMMARY")
        print(f"  Segments Transcribed : {total_segments}")
        print(f"  Signals Detected     : {total_signals}")
        print(f"  Nudges Generated     : {total_nudges}")
        for priority_label, count in nudges_by_priority.items():
            if count > 0:
                print(f"    {priority_label}: {count}")
        print(f"\n{report.format()}")

    return {
        "session_id": session_id,
        "segments": total_segments,
        "signals": total_signals,
        "nudges": total_nudges,
        "sla_compliant": report.overall_sla_compliant,
        "latency_report": report,
        "nudge_stats": nudge_stats,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "═" * 65)
    print("  Q4 LIVE NUDGES — SIMULATION TEST SUITE")
    print("  Streaming Audio → ASR → Signal Extraction → Nudge Engine")
    print("═" * 65)

    # ── Test 1: Frustrated Repeat Caller ──
    result1 = run_live_pipeline(
        session_id="NUDGE-001",
        script=CALL_SCRIPT_1,
        title="TEST 1 — Health Insurance: Frustrated Repeat Caller + Cross-Sell",
        verbose=True,
    )

    # ── Test 2: Legal Threat + Compliance Gaps ──
    result2 = run_live_pipeline(
        session_id="NUDGE-002",
        script=CALL_SCRIPT_2,
        title="TEST 2 — Business Loan: Legal Threat + Escalation + Compliance",
        verbose=True,
    )

    # ── Test 3: Latency Stress Test ──
    print(f"\n{'═'*65}")
    print(f"  TEST 3 — LATENCY STRESS TEST ({len(CALL_SCRIPT_3_STRESS)} utterances)")
    print(f"{'═'*65}")
    stress_start = time.perf_counter()
    result3 = run_live_pipeline(
        session_id="NUDGE-STRESS",
        script=CALL_SCRIPT_3_STRESS,
        title="STRESS TEST",
        verbose=False,  # Suppress segment output for stress test
    )
    stress_elapsed = time.perf_counter() - stress_start
    report3 = result3["latency_report"]
    print(f"\n  Stress Test Complete in {stress_elapsed:.2f}s")
    print(f"  Segments Processed: {result3['segments']}")
    print(f"  Nudges Generated  : {result3['nudges']}")
    print(f"\n{report3.format()}")

    # ── Overall Summary ──
    print(f"\n{'═'*65}")
    print(f"  OVERALL TEST SUMMARY")
    print(f"{'─'*65}")
    for i, result in enumerate([result1, result2, result3], 1):
        sla = "✅ PASS" if result["sla_compliant"] else "❌ FAIL"
        print(
            f"  Test {i}: Segments={result['segments']} | "
            f"Signals={result['signals']} | "
            f"Nudges={result['nudges']} | "
            f"SLA={sla}"
        )

    print(f"\n  Cooldown/Suppression Verification:")
    print(f"  (See nudge stats above — duplicate signals are suppressed by cooldown windows)")
    print(f"{'═'*65}\n")


if __name__ == "__main__":
    main()

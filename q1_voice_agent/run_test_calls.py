"""
Q1 Voice Agent — Simulated Test Calls
======================================
Simulates 3 realistic call scenarios and prints full transcripts with
grounding traces. Each call tests different aspects of the agent:

  Call 1: Cooperative customer — Health Insurance
          Complete qualification, no objections, reaches QUALIFIED state.

  Call 2: Objecting customer — Business Loan
          Multiple objections (interest rate, documents), handles them,
          asks out-of-scope question, eventually resolves.

  Call 3: Escalation + Incomplete info — Health Insurance
          Customer provides incomplete information, out-of-scope question,
          then explicitly requests a human supervisor (escalation).

All calls produce full transcripts with state logs and grounding citations.
"""

from __future__ import annotations

import logging
import sys
import os
import time

# Ensure project root is on path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.WARNING)

from q1_voice_agent.agent_brain import VoiceAgentBrain


# ---------------------------------------------------------------------------
# Simulated Dialogues
# ---------------------------------------------------------------------------

CALL_1_DIALOGUE = [
    "I'm interested in getting health insurance for myself.",
    "I'm 34 years old.",
    "No, I don't have any pre-existing conditions. I'm pretty healthy.",
    "I can probably spend around PHP 1,000 a month on premiums.",
    "I want inpatient hospitalization and outpatient coverage. Maybe dental too.",
    "Yes, that sounds great! I'd like to apply.",
    "What documents do I need to submit?",
]

CALL_2_DIALOGUE = [
    "I'm looking for a business loan for my retail store.",
    "We've been running for 3 years.",
    "Around PHP 400,000 per month in sales.",
    "I want to borrow about PHP 1,500,000.",
    "No, I don't have collateral property. Just the store inventory.",
    "No defaults. My credit is clean.",
    "The interest rate sounds really high though. 1.75% a month? That's steep.",
    "What if I can't gather all the documents they require?",
    "Okay, can you explain what the effective interest rate means exactly?",
    "Fine, let's proceed with the application.",
]

CALL_3_DIALOGUE = [
    "Hello, I want information about your health insurance.",
    "Fifty-five. Wait, actually — can you tell me if you cover pre-existing heart conditions?",
    "What about the free look period? How does that work?",
    "I'm not sure I understand all this. I don't really know my budget.",
    "This is all too complicated. Can I speak to a manager please?",
]


# ---------------------------------------------------------------------------
# Call Runner
# ---------------------------------------------------------------------------

def run_call(
    brain: VoiceAgentBrain,
    session_id: str,
    dialogue: list[str],
    call_title: str,
    include_grounding: bool = True,
) -> None:
    """Run a simulated call and print the full transcript."""
    sep = "═" * 65

    print(f"\n{sep}")
    print(f"  {call_title}")
    print(f"  Session ID: {session_id}")
    print(sep)

    # Start the call
    opening, session = brain.start_call(session_id)
    print(f"\n  [AGENT OPENING]\n  {opening}\n")

    turn = 1
    for customer_utterance in dialogue:
        print(f"  ─── Turn {turn} ───")
        print(f"  CUSTOMER : {customer_utterance}")
        time.sleep(0.05)  # Simulate realistic processing delay

        response = brain.process_turn(session_id, customer_utterance)
        print(f"  AGENT    : {response}\n")
        turn += 1

        # Stop if terminal state
        if session.final_state in ("qualified", "disqualified", "escalation", "call_ended"):
            break

    # Print full transcript with grounding traces
    print("\n" + session.transcript(include_grounding=include_grounding))
    print(f"\n  Lead Profile:")
    flow = brain._sessions.get(f"_flow_{session_id}")
    if flow:
        print(flow.lead.to_summary())

    # Print grounding summary
    grounded_turns = [t for t in session.turns if t.grounded]
    print(f"\n  Grounding Summary: {len(grounded_turns)} turn(s) used KB retrieval.")
    for t in grounded_turns:
        print(f"    Turn {t.turn_index}: Query='{t.kb_query_used[:50] if t.kb_query_used else ''}...'")
        for cite in t.citations_used:
            print(f"      → {cite}")

    print(f"\n  Transitions Logged: {len(flow.transitions) if flow else 0}")
    if flow:
        for tr in flow.transitions[-5:]:  # Show last 5 transitions
            print(f"    {tr.from_state.value} → {tr.to_state.value} ('{tr.trigger}')")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n" + "═" * 65)
    print("  Q1 VOICE AGENT — SIMULATED TEST CALLS")
    print("  Grounded RAG Brain + Qualification State Machine")
    print("═" * 65)
    print("\n  Initializing VoiceAgentBrain (loading knowledge base)...")

    build_start = time.perf_counter()
    brain = VoiceAgentBrain()
    build_time = (time.perf_counter() - build_start) * 1000
    print(f"  Brain initialized in {build_time:.1f}ms.\n")

    # ── Call 1: Cooperative Health Insurance Customer ──
    run_call(
        brain=brain,
        session_id="TEST-001",
        dialogue=CALL_1_DIALOGUE,
        call_title="CALL 1 — Health Insurance: Cooperative Customer (Full Qualification)",
    )

    # ── Call 2: Objecting Business Loan Customer ──
    run_call(
        brain=brain,
        session_id="TEST-002",
        dialogue=CALL_2_DIALOGUE,
        call_title="CALL 2 — Business Loan: Objecting Customer (Multiple Objections + Out-of-Scope)",
    )

    # ── Call 3: Escalation Request ──
    run_call(
        brain=brain,
        session_id="TEST-003",
        dialogue=CALL_3_DIALOGUE,
        call_title="CALL 3 — Health Insurance: Incomplete Info + Escalation Request",
    )

    print("\n" + "═" * 65)
    print("  ALL TEST CALLS COMPLETED")
    print("═" * 65 + "\n")


if __name__ == "__main__":
    main()

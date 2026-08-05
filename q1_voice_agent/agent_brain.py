"""
Q1 Voice Agent — Grounded RAG Brain
=====================================
The VoiceAgentBrain is the intelligence layer of the voice agent.
It combines:

  1. The QualificationFlow state machine (structured lead capture)
  2. The HybridRetriever (knowledge-grounded responses)
  3. A response composer that NEVER hallucinate — it either uses
     retrieved knowledge or explicitly states "information unavailable"

Grounding guarantee:
  - Every factual claim in a response is backed by a retrieved knowledge record.
  - If no relevant knowledge is found, the agent uses a safe fallback.
  - All citations are tracked in the conversation log for auditability.
"""

from __future__ import annotations

import logging
import re
import sys
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Ensure project root on path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from q2_knowledge_base.retriever import HybridRetriever
from q1_voice_agent.qualification_flow import (
    CallState,
    QualificationFlow,
    UseCase,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Grounding Constants
# ---------------------------------------------------------------------------

_FALLBACK_RESPONSE = (
    "That's a great question. I want to make sure I give you accurate information, "
    "so let me connect you with one of our specialists who can provide precise details "
    "on that topic. Is that okay with you?"
)

_OUT_OF_SCOPE_RESPONSE = (
    "I appreciate your question. However, that topic is outside what I'm able to assist with today. "
    "I'm specifically here to help with Health Insurance plans and Business Loan products. "
    "Is there anything related to those that I can help you with?"
)

# These query patterns trigger a knowledge base lookup before responding
_KB_TRIGGER_PATTERNS = [
    r"what (is|are|does|do|can)",
    r"how (much|many|do|does|can|long)",
    r"explain",
    r"tell me about",
    r"(coverage|benefit|premium|rider|deductible|exclusion|waiting period)",
    r"(interest rate|tenor|collateral|documents|requirements|qualify)",
    r"(pre.?existing|eligib|underwriting)",
    r"(claim|reimburse|file|process)",
    r"(cancel|renew|upgrade|downgrade)",
    r"(penalty|fee|charge|cost|price)",
]

_KB_TRIGGER_REGEX = re.compile(
    "|".join(_KB_TRIGGER_PATTERNS), re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class Turn:
    """A single conversational turn with full grounding trace."""
    turn_index: int
    user_input: str
    agent_response: str
    call_state: str
    kb_query_used: Optional[str] = None
    citations_used: List[str] = field(default_factory=list)
    grounded: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CallSession:
    """Full record of a voice agent call session."""
    session_id: str
    use_case: Optional[str] = None
    turns: List[Turn] = field(default_factory=list)
    final_state: str = ""
    outcome: str = "pending"
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None

    def transcript(self, include_grounding: bool = False) -> str:
        """Generate a human-readable call transcript."""
        lines = [
            f"{'='*65}",
            f"CALL TRANSCRIPT | Session: {self.session_id}",
            f"Use Case: {self.use_case or 'Unknown'} | Outcome: {self.outcome}",
            f"{'='*65}",
        ]
        for turn in self.turns:
            lines.append(f"\n[Turn {turn.turn_index}] State: {turn.call_state}")
            lines.append(f"  CUSTOMER : {turn.user_input}")
            lines.append(f"  AGENT    : {turn.agent_response}")
            if include_grounding and turn.grounded and turn.citations_used:
                lines.append(f"  SOURCES  : {', '.join(turn.citations_used[:2])}")
        lines.append(f"\n{'='*65}")
        lines.append(f"Final State: {self.final_state} | Outcome: {self.outcome}")
        if self.ended_at:
            duration = (self.ended_at - self.started_at).total_seconds()
            lines.append(f"Duration   : {duration:.0f}s")
        lines.append(f"{'='*65}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Voice Agent Brain
# ---------------------------------------------------------------------------

class VoiceAgentBrain:
    """
    Knowledge-grounded voice agent brain.

    Combines the QualificationFlow state machine with the HybridRetriever
    to produce grounded, citation-backed responses on every turn.

    Grounding Logic:
    - For qualification questions (age, budget, etc.) → state machine response
    - For informational/factual questions → KB lookup → grounded response
    - If KB returns no results → safe fallback (never hallucinate)
    - For out-of-scope topics → explicit out-of-scope redirect
    """

    def __init__(self, retriever: Optional[HybridRetriever] = None) -> None:
        # Initialize and build the knowledge retriever
        self._retriever = retriever or HybridRetriever()
        if not self._retriever._is_built:
            self._retriever.build()

        self._sessions: Dict[str, CallSession] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_call(self, session_id: str = "") -> Tuple[str, CallSession]:
        """
        Start a new call session.
        Returns (opening_message, session).
        """
        import uuid
        session_id = session_id or str(uuid.uuid4())[:8]

        flow = QualificationFlow(session_id=session_id)
        opening = flow.get_opening_message()

        session = CallSession(session_id=session_id)
        session.turns.append(Turn(
            turn_index=0,
            user_input="[CALL STARTED]",
            agent_response=opening,
            call_state=CallState.GREETING.value,
            grounded=False,
        ))

        # Store both session and flow together
        self._sessions[session_id] = session
        self._sessions[f"_flow_{session_id}"] = flow  # type: ignore

        return opening, session

    def process_turn(self, session_id: str, user_input: str) -> str:
        """
        Process a single customer utterance and return the agent response.

        The brain:
          1. Checks if the input is an informational question → KB lookup
          2. Runs the qualification flow state machine
          3. Optionally augments the state machine response with KB context
          4. Returns the final grounded response
        """
        session: CallSession = self._sessions.get(session_id)  # type: ignore
        flow: QualificationFlow = self._sessions.get(f"_flow_{session_id}")  # type: ignore

        if not session or not flow:
            return "I'm sorry, I couldn't find your session. Please call back and we'll assist you."

        turn_index = len(session.turns)

        # Step 2: Run the state machine FIRST to advance state
        current_state = flow.current_state
        new_state, flow_response = flow.process(user_input)

        # Step 1: Check if the input warrants a KB lookup
        # Never override the state machine during use-case detection or qualification states
        _DETECTION_STATES = {CallState.GREETING, CallState.USE_CASE_DETECTION}
        kb_query = None
        citations_used = []
        grounded = False
        kb_augmentation = ""

        if (
            self._is_informational_query(user_input)
            and current_state not in _DETECTION_STATES
            and new_state not in _DETECTION_STATES
        ):
            kb_query = user_input
            context = self._retriever.get_context_for_agent(user_input, top_k=2)

            if context != "NO_CONTEXT_FOUND":
                kb_results = self._retriever.search(user_input, top_k=2)
                citations_used = [r.citation for r in kb_results]
                kb_augmentation = self._compose_grounded_answer(user_input, context)
                grounded = True
            else:
                kb_augmentation = _FALLBACK_RESPONSE

        # Step 3: Compose final response
        if kb_augmentation and not self._is_qualification_state(current_state):
            # For pure informational queries outside qualification flow,
            # use the KB-grounded response exclusively
            final_response = kb_augmentation
        else:
            # Use state machine response — always wins during use-case detection
            final_response = flow_response

        # Step 4: Update session
        if flow.lead.use_case:
            session.use_case = flow.lead.use_case.value
        session.final_state = new_state.value
        session.outcome = flow.lead.qualification_outcome.value

        session.turns.append(Turn(
            turn_index=turn_index,
            user_input=user_input,
            agent_response=final_response,
            call_state=new_state.value,
            kb_query_used=kb_query,
            citations_used=citations_used,
            grounded=grounded,
        ))

        # Mark session ended if terminal state
        if new_state in (
            CallState.QUALIFIED, CallState.DISQUALIFIED,
            CallState.CALL_ENDED, CallState.ESCALATION
        ):
            session.ended_at = datetime.utcnow()

        return final_response

    def get_session(self, session_id: str) -> Optional[CallSession]:
        """Return the full call session record."""
        return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _is_informational_query(self, text: str) -> bool:
        """Detect if the user input is an informational question (not a qualification answer)."""
        return bool(_KB_TRIGGER_REGEX.search(text))

    def _is_qualification_state(self, state: CallState) -> bool:
        """Check if the current state is actively collecting qualification data."""
        qualification_states = {
            CallState.HI_AGE, CallState.HI_PRE_EXISTING, CallState.HI_BUDGET,
            CallState.HI_COVERAGE_NEEDS, CallState.HI_RECOMMENDATION,
            CallState.BL_BUSINESS_TYPE, CallState.BL_OPERATING_YEARS,
            CallState.BL_MONTHLY_REVENUE, CallState.BL_LOAN_AMOUNT,
            CallState.BL_COLLATERAL, CallState.BL_CREDIT_HISTORY,
            CallState.BL_RECOMMENDATION,
        }
        return state in qualification_states

    def _compose_grounded_answer(self, query: str, context: str) -> str:
        """
        Compose a grounded answer from KB context.
        Extracts key facts from retrieved context and wraps in a conversational response.
        Never invents facts — only uses what is in the context.
        """
        # Extract first meaningful paragraph from context
        context_clean = context.replace("[Source:", "\n[Source:").strip()
        paragraphs = [p.strip() for p in context_clean.split("\n\n") if p.strip()]

        if not paragraphs:
            return _FALLBACK_RESPONSE

        # Take the first substantive block of text
        first_block = paragraphs[0]

        # Strip source citation header for display
        lines = first_block.splitlines()
        content_lines = [l for l in lines if not l.startswith("[Source:") and not l.startswith("Category:")]
        content = " ".join(content_lines).strip()

        if len(content) < 30:
            return _FALLBACK_RESPONSE

        # Truncate to conversational length
        if len(content) > 400:
            content = content[:400].rsplit(".", 1)[0] + "."

        return (
            f"Based on our product information: {content} "
            "Would you like me to go into more detail on any specific aspect?"
        )

"""
Q4 Live Nudges — Nudge Control Engine
=======================================
The NudgeEngine is the final stage of the live insights pipeline.
It converts raw DetectedSignals into actionable, prioritized Nudges
that are surfaced to the agent in real time.

Key Responsibilities:
  1. Signal → Nudge Transformation — Format signals into agent-facing nudges
  2. Priority Scoring — Rank nudges by urgency and business impact
  3. Deduplication — Prevent the same nudge from firing twice in quick succession
  4. Cooldown Management — Per-signal-type suppression windows
  5. Suppression Rules — Do not surface low-priority nudges during high-priority events
  6. False-Positive Filtering — Confidence threshold gates
  7. Display Formatting — Rich text for dashboard rendering

Nudge Priority Levels:
  CRITICAL (5) — Immediate action required (legal threat, escalation)
  HIGH (4)     — Compliance gaps, strong frustration signals
  MEDIUM (3)   — Cross-sell opportunity, payment difficulty
  LOW (2)      — Positive sentiment, soft buying signals
  INFO (1)     — General context / background nudges
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from .signal_extractor import DetectedSignal, SignalType


# ---------------------------------------------------------------------------
# Nudge Priority
# ---------------------------------------------------------------------------

class NudgePriority(int, Enum):
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5

    def label(self) -> str:
        return {1: "ℹ INFO", 2: "🔵 LOW", 3: "🟡 MEDIUM", 4: "🔴 HIGH", 5: "🚨 CRITICAL"}[self.value]


# ---------------------------------------------------------------------------
# Nudge Model
# ---------------------------------------------------------------------------

@dataclass
class Nudge:
    """
    A single actionable nudge surfaced to the agent's dashboard.
    Contains the recommended action, context, and display formatting.
    """
    nudge_id: str
    session_id: str
    signal_id: str
    signal_type: SignalType
    priority: NudgePriority
    title: str
    body: str                    # The agent-facing recommendation text
    supporting_text: str         # What the customer said (context for agent)
    confidence: float
    is_active: bool = True       # False once dismissed or superseded
    created_at: float = field(default_factory=time.perf_counter)
    dismissed_at: Optional[float] = None
    displayed_for_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "nudge_id": self.nudge_id,
            "session_id": self.session_id,
            "signal_type": self.signal_type.value,
            "priority": self.priority.value,
            "priority_label": self.priority.label(),
            "title": self.title,
            "body": self.body,
            "supporting_text": self.supporting_text,
            "confidence": round(self.confidence, 3),
            "is_active": self.is_active,
            "created_at": self.created_at,
        }

    def dismiss(self) -> None:
        """Mark this nudge as dismissed by the agent."""
        self.is_active = False
        self.dismissed_at = time.perf_counter()
        if self.dismissed_at:
            self.displayed_for_ms = (self.dismissed_at - self.created_at) * 1000

    def format_display(self) -> str:
        """Return a formatted string for terminal/dashboard display."""
        return (
            f"┌─ {self.priority.label()} NUDGE ─────────────────────────────\n"
            f"│ {self.title}\n"
            f"│ \n"
            f"│ 💬 Context: \"{self.supporting_text[:80]}...\"\n"
            f"│            (if longer)\n"
            f"│ \n"
            f"│ ✅ Action: {self.body}\n"
            f"│ Confidence: {self.confidence:.0%}\n"
            f"└────────────────────────────────────────────────────"
        ).replace("...\"\n│            (if longer)", "\"" if len(self.supporting_text) <= 80 else "...\"")


# ---------------------------------------------------------------------------
# Nudge Templates
# ---------------------------------------------------------------------------

_NUDGE_TEMPLATES: Dict[str, Dict] = {
    SignalType.COMPLIANCE_GAP.value + "_missing_eir_disclosure": {
        "priority": NudgePriority.HIGH,
        "title": "⚠️ Compliance: Disclose Effective Interest Rate",
        "body": "Say: 'The Effective Interest Rate (EIR) for this loan is X% per annum. This is different from the nominal rate and represents the true cost of credit.'",
    },
    SignalType.COMPLIANCE_GAP.value + "_missing_exclusion_disclosure": {
        "priority": NudgePriority.HIGH,
        "title": "⚠️ Compliance: Mention Key Exclusions",
        "body": "State the 3 key exclusions: (1) Pre-existing conditions — 12-month exclusion, (2) 30-day waiting period for illnesses, (3) Out-of-network providers not covered.",
    },
    SignalType.COMPLIANCE_GAP.value + "_missing_free_look_disclosure": {
        "priority": NudgePriority.HIGH,
        "title": "⚠️ Compliance: Mention Free Look Period",
        "body": "Inform customer: 'You have a 15-day Free Look Period from policy receipt to return the policy for a full premium refund, no questions asked.'",
    },
    SignalType.COMPLIANCE_GAP.value + "_missing_penalty_disclosure": {
        "priority": NudgePriority.MEDIUM,
        "title": "⚠️ Compliance: Disclose Penalty Terms",
        "body": "Disclose: 'A late payment fee of 3% per annum applies to overdue principal. Three missed payments may trigger loan restructuring.'",
    },
    SignalType.CUSTOMER_FRUSTRATION.value + "_repeated_calling": {
        "priority": NudgePriority.HIGH,
        "title": "🔴 Customer Called Multiple Times — Empathize Now",
        "body": "Say: 'I sincerely apologize that you've had to contact us multiple times about this. I'm personally taking ownership of this issue and will resolve it before this call ends.'",
    },
    SignalType.CUSTOMER_FRUSTRATION.value + "_service_dissatisfaction": {
        "priority": NudgePriority.HIGH,
        "title": "🔴 High Frustration Detected",
        "body": "Lower your voice, slow down, and acknowledge. Say: 'I completely understand your frustration, and I take full responsibility for ensuring you're taken care of today.'",
    },
    SignalType.CROSS_SELL_OPPORTUNITY.value + "_family_mention": {
        "priority": NudgePriority.MEDIUM,
        "title": "💡 Cross-Sell: Family Plan Opportunity",
        "body": "Introduce: 'By the way, we have a Family Plan that covers your spouse and up to 3 children at a 15% bundle discount. Would you like me to include them in a quick quote?'",
    },
    SignalType.CROSS_SELL_OPPORTUNITY.value + "_secondary_product_interest": {
        "priority": NudgePriority.MEDIUM,
        "title": "💡 Cross-Sell: Secondary Product Interest",
        "body": "Customer shows interest in another product. Briefly introduce it: 'That's something we can definitely help with. Let me share a quick overview — it'll only take 60 seconds.'",
    },
    SignalType.PAYMENT_DIFFICULTY.value + "_affordability_concern": {
        "priority": NudgePriority.MEDIUM,
        "title": "💰 Payment Concern — Offer Flexible Options",
        "body": "Show daily cost: 'That's only PHP 40 per day — less than a coffee!' Offer: (1) Lower tier plan, (2) Annual payment for 5% discount, (3) Smaller sum assured.",
    },
    SignalType.PAYMENT_DIFFICULTY.value + "_irregular_income": {
        "priority": NudgePriority.LOW,
        "title": "💰 Irregular Income — Mention Annual Payment",
        "body": "Offer: 'For self-employed clients, we recommend annual payment which also saves you 5% on total premium. Would that work better for you?'",
    },
    SignalType.LEGAL_THREAT.value + "_generic": {
        "priority": NudgePriority.CRITICAL,
        "title": "🚨 LEGAL THREAT — ESCALATE IMMEDIATELY",
        "body": "DO NOT argue or deny. Say: 'I completely understand your concern. I'm escalating this to our Compliance Officer immediately.' Then transfer the call NOW.",
    },
    SignalType.POSITIVE_SENTIMENT.value + "_generic": {
        "priority": NudgePriority.LOW,
        "title": "✅ Buying Signal Detected — Close Now",
        "body": "This is a closing moment. Say: 'Wonderful! Let me help you get started right now. I just need a few details to process your application today.'",
    },
    SignalType.ESCALATION_REQUEST.value + "_generic": {
        "priority": NudgePriority.CRITICAL,
        "title": "🚨 Customer Requesting Supervisor",
        "body": "Transfer immediately. Say: 'Of course. I'm connecting you to a senior specialist right now. Please hold for just a moment.'",
    },
    SignalType.OBJECTION.value + "_generic": {
        "priority": NudgePriority.MEDIUM,
        "title": "💬 Objection Detected",
        "body": "Acknowledge the concern first ('I understand...'), then address it with a specific response from the objection handling guide.",
    },
}

_DEFAULT_TEMPLATE = {
    "priority": NudgePriority.INFO,
    "title": "ℹ️ Signal Detected",
    "body": "Review the customer's last statement and respond thoughtfully.",
}


# ---------------------------------------------------------------------------
# Nudge Engine
# ---------------------------------------------------------------------------

class NudgeEngine:
    """
    Converts DetectedSignals into prioritized, deduplicated Nudges.

    Control flow:
    1. Receive DetectedSignal from SignalExtractor
    2. Check cooldown — was this signal type recently fired?
    3. Check suppression — is a higher-priority nudge already active?
    4. Deduplicate — is an identical nudge already displayed?
    5. Generate Nudge from template
    6. Emit Nudge to dashboard callback

    Usage:
        engine = NudgeEngine(session_id="call-001")
        engine.on_nudge(lambda nudge: print(nudge.format_display()))
        nudge = engine.process_signal(detected_signal)
    """

    # Suppression: while CRITICAL or HIGH nudge is active, suppress LOW/INFO
    ACTIVE_HIGH_SUPPRESSES_LOW = True

    def __init__(self, session_id: str = "") -> None:
        self.session_id = session_id
        self._all_nudges: List[Nudge] = []
        self._active_nudges: List[Nudge] = []
        self._callbacks: List = []
        self._cooldown_tracker: Dict[str, float] = {}  # signal_key → last_fired_time
        self._suppressed_signal_ids: Set[str] = set()
        self._nudge_counter = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on_nudge(self, callback) -> None:
        """Register a callback to be called when a new nudge is emitted."""
        self._callbacks.append(callback)

    def process_signal(self, signal: DetectedSignal) -> Optional[Nudge]:
        """
        Process a single DetectedSignal and optionally emit a Nudge.

        Returns the generated Nudge if emitted, None if suppressed.
        """
        # Step 1: Confidence gate
        if signal.confidence < 0.60:
            return None

        # Step 2: Cooldown check
        cooldown_key = f"{signal.signal_type.value}_{signal.sub_type.value}"
        if self._is_in_cooldown(cooldown_key, signal):
            return None

        # Step 3: Suppression check
        if self._is_suppressed(signal):
            return None

        # Step 4: Generate nudge from template
        nudge = self._create_nudge(signal)

        # Step 5: Register and emit
        self._cooldown_tracker[cooldown_key] = time.perf_counter()
        self._all_nudges.append(nudge)
        self._active_nudges.append(nudge)
        self._nudge_counter += 1

        for callback in self._callbacks:
            callback(nudge)

        return nudge

    def process_signals(self, signals: List[DetectedSignal]) -> List[Nudge]:
        """Process a list of signals, returning all emitted nudges."""
        emitted = []
        for signal in signals:
            nudge = self.process_signal(signal)
            if nudge:
                emitted.append(nudge)
        return emitted

    def dismiss_nudge(self, nudge_id: str) -> bool:
        """Mark a nudge as dismissed by the agent."""
        for nudge in self._active_nudges:
            if nudge.nudge_id == nudge_id:
                nudge.dismiss()
                self._active_nudges.remove(nudge)
                return True
        return False

    def get_active_nudges(self) -> List[Nudge]:
        """Return all currently active (undismissed) nudges, sorted by priority."""
        return sorted(
            [n for n in self._active_nudges if n.is_active],
            key=lambda n: (-n.priority.value, n.created_at),
        )

    def get_all_nudges(self) -> List[Nudge]:
        """Return complete history of all generated nudges."""
        return list(self._all_nudges)

    def get_statistics(self) -> Dict:
        """Return nudge engine statistics for dashboard/logging."""
        by_priority = {}
        by_type = {}
        for nudge in self._all_nudges:
            p = nudge.priority.label()
            by_priority[p] = by_priority.get(p, 0) + 1
            t = nudge.signal_type.value
            by_type[t] = by_type.get(t, 0) + 1

        dismissed = sum(1 for n in self._all_nudges if not n.is_active)
        return {
            "total_nudges": len(self._all_nudges),
            "active_nudges": len(self._active_nudges),
            "dismissed_nudges": dismissed,
            "total_suppressed": self._nudge_counter - len(self._all_nudges),
            "by_priority": by_priority,
            "by_signal_type": by_type,
        }

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _is_in_cooldown(self, cooldown_key: str, signal: DetectedSignal) -> bool:
        """Check if this signal type is within its cooldown window."""
        if cooldown_key not in self._cooldown_tracker:
            return False

        # Get the cooldown window from the corresponding detection rule
        from .signal_extractor import _DETECTION_RULES
        cooldown_s = 120.0  # Default
        for rule in _DETECTION_RULES:
            if rule.signal_type == signal.signal_type and rule.sub_type == signal.sub_type:
                cooldown_s = rule.suppression_window_s
                break

        elapsed = time.perf_counter() - self._cooldown_tracker[cooldown_key]
        return elapsed < cooldown_s

    def _is_suppressed(self, signal: DetectedSignal) -> bool:
        """
        Check if this signal should be suppressed based on active nudges.
        LOW/INFO nudges are suppressed when CRITICAL/HIGH are active.
        """
        if not self.ACTIVE_HIGH_SUPPRESSES_LOW:
            return False

        # Check if any CRITICAL or HIGH nudge is currently active
        high_active = any(
            n.priority in (NudgePriority.CRITICAL, NudgePriority.HIGH)
            for n in self._active_nudges
            if n.is_active
        )

        if high_active:
            new_priority = self._get_priority_for_signal(signal)
            return new_priority in (NudgePriority.LOW, NudgePriority.INFO)

        return False

    def _get_priority_for_signal(self, signal: DetectedSignal) -> NudgePriority:
        """Determine the priority level for a given signal."""
        template_key = f"{signal.signal_type.value}_{signal.sub_type.value}"
        template = _NUDGE_TEMPLATES.get(template_key, _DEFAULT_TEMPLATE)
        return template["priority"]

    def _create_nudge(self, signal: DetectedSignal) -> Nudge:
        """Build a Nudge from a DetectedSignal using the template library."""
        template_key = f"{signal.signal_type.value}_{signal.sub_type.value}"
        template = _NUDGE_TEMPLATES.get(template_key, _DEFAULT_TEMPLATE)

        # Truncate supporting text for display
        supporting = signal.segment_text
        if len(supporting) > 120:
            supporting = supporting[:120] + "..."

        return Nudge(
            nudge_id=str(uuid.uuid4())[:8],
            session_id=self.session_id,
            signal_id=signal.signal_id,
            signal_type=signal.signal_type,
            priority=template["priority"],
            title=template["title"],
            body=template["body"],
            supporting_text=supporting,
            confidence=signal.confidence,
        )

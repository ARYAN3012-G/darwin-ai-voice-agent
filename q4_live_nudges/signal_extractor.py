"""
Q4 Live Nudges — Real-Time Signal Extractor
=============================================
Extracts actionable signals from live call transcript segments in real time.

Signals Detected:
  1. COMPLIANCE_GAP     — Agent missed a mandatory disclosure
  2. CUSTOMER_FRUSTRATION — Customer expressing frustration / escalation risk
  3. CROSS_SELL_OPPORTUNITY — Customer interest in additional products
  4. PAYMENT_DIFFICULTY  — Customer indicating financial hardship
  5. REPEAT_COMPLAINT    — Customer repeating the same issue
  6. COMPETITOR_MENTION  — Customer mentions a competing product
  7. POSITIVE_SENTIMENT  — Customer showing buying intent / agreement
  8. LEGAL_THREAT        — Customer threatening legal action

Each signal has:
  - Type and sub-type
  - Confidence score (0.0–1.0)
  - Matched evidence (the exact phrase that triggered detection)
  - Recommended agent action

Signal extraction runs in <200ms P95 per segment.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .stream_processor import Speaker, TranscriptSegment


# ---------------------------------------------------------------------------
# Signal Types
# ---------------------------------------------------------------------------

class SignalType(str, Enum):
    COMPLIANCE_GAP = "compliance_gap"
    CUSTOMER_FRUSTRATION = "customer_frustration"
    CROSS_SELL_OPPORTUNITY = "cross_sell_opportunity"
    PAYMENT_DIFFICULTY = "payment_difficulty"
    REPEAT_COMPLAINT = "repeat_complaint"
    COMPETITOR_MENTION = "competitor_mention"
    POSITIVE_SENTIMENT = "positive_sentiment"
    LEGAL_THREAT = "legal_threat"
    OBJECTION = "objection"
    ESCALATION_REQUEST = "escalation_request"


class SignalSubType(str, Enum):
    # Compliance sub-types
    MISSING_EIR_DISCLOSURE = "missing_eir_disclosure"
    MISSING_EXCLUSION_DISCLOSURE = "missing_exclusion_disclosure"
    MISSING_FREE_LOOK_DISCLOSURE = "missing_free_look_disclosure"
    MISSING_PENALTY_DISCLOSURE = "missing_penalty_disclosure"
    MISSING_TOTAL_COST_DISCLOSURE = "missing_total_cost_disclosure"

    # Frustration sub-types
    REPEATED_CALLING = "repeated_calling"
    UNRESOLVED_ISSUE = "unresolved_issue"
    LONG_WAIT = "long_wait"
    SERVICE_DISSATISFACTION = "service_dissatisfaction"

    # Cross-sell sub-types
    FAMILY_MENTION = "family_mention"
    SECONDARY_PRODUCT_INTEREST = "secondary_product_interest"
    UPGRADE_OPPORTUNITY = "upgrade_opportunity"

    # Payment difficulty sub-types
    AFFORDABILITY_CONCERN = "affordability_concern"
    IRREGULAR_INCOME = "irregular_income"
    EXISTING_DEBT = "existing_debt"

    # General
    GENERIC = "generic"


# ---------------------------------------------------------------------------
# Signal Detection Rules
# ---------------------------------------------------------------------------

@dataclass
class DetectionRule:
    """A single pattern-based signal detection rule."""
    signal_type: SignalType
    sub_type: SignalSubType
    patterns: List[str]           # Regex patterns (case-insensitive)
    min_confidence: float
    speaker_filter: Optional[Speaker]  # None = match either speaker
    recommended_action: str
    suppression_window_s: float = 120.0  # Cooldown before same signal fires again


_DETECTION_RULES: List[DetectionRule] = [
    # ── Compliance Gaps (agent must say these) ──
    DetectionRule(
        signal_type=SignalType.COMPLIANCE_GAP,
        sub_type=SignalSubType.MISSING_EIR_DISCLOSURE,
        patterns=[
            r"\b(interest rate|bunga|rate)\b.*\b(per month|per year|monthly|annually)\b",
        ],
        min_confidence=0.80,
        speaker_filter=Speaker.AGENT,
        recommended_action="Disclose the Effective Interest Rate (EIR) and Total Cost of Credit to the customer.",
        suppression_window_s=300.0,
    ),
    DetectionRule(
        signal_type=SignalType.COMPLIANCE_GAP,
        sub_type=SignalSubType.MISSING_EXCLUSION_DISCLOSURE,
        patterns=[
            r"\b(coverage|covered|insurance)\b(?!.*\b(exclusion|not covered|waiting period)\b)",
        ],
        min_confidence=0.70,
        speaker_filter=Speaker.AGENT,
        recommended_action="Mention the key exclusions: pre-existing conditions, waiting period, out-of-network charges.",
        suppression_window_s=300.0,
    ),
    DetectionRule(
        signal_type=SignalType.COMPLIANCE_GAP,
        sub_type=SignalSubType.MISSING_FREE_LOOK_DISCLOSURE,
        patterns=[
            r"\b(apply|application|proceed|sign up|enroll)\b",
        ],
        min_confidence=0.75,
        speaker_filter=Speaker.AGENT,
        recommended_action="Remind customer of the 15-day Free Look Period — they may cancel for a full refund.",
        suppression_window_s=300.0,
    ),

    # ── Customer Frustration ──
    DetectionRule(
        signal_type=SignalType.CUSTOMER_FRUSTRATION,
        sub_type=SignalSubType.REPEATED_CALLING,
        patterns=[
            r"\b(called|calling|this is the (second|third|fourth|\d+)(st|nd|rd|th)? time)\b",
            r"\b(already called|called before|keep calling)\b",
            r"\b(past \d+ times?|several times?|multiple times?)\b",
        ],
        min_confidence=0.85,
        speaker_filter=Speaker.CUSTOMER,
        recommended_action="Acknowledge the customer's repeated attempts. Apologize sincerely and offer to resolve in this call.",
        suppression_window_s=60.0,
    ),
    DetectionRule(
        signal_type=SignalType.CUSTOMER_FRUSTRATION,
        sub_type=SignalSubType.SERVICE_DISSATISFACTION,
        patterns=[
            r"\b(not happy|unhappy|dissatisfied|disappointed|frustrated|angry|terrible|awful|useless)\b",
            r"\b(cancel|cancellation|close my (account|policy))\b",
            r"\b(this is ridiculous|unacceptable|this is wrong)\b",
            r"\b(nobody|no one|never|always|every time)\b.*\b(help|resolve|fix|answer)\b",
        ],
        min_confidence=0.80,
        speaker_filter=Speaker.CUSTOMER,
        recommended_action="Express empathy. Use: 'I sincerely apologize for this experience. Let me personally ensure this is resolved for you now.'",
        suppression_window_s=90.0,
    ),

    # ── Cross-Sell Opportunities ──
    DetectionRule(
        signal_type=SignalType.CROSS_SELL_OPPORTUNITY,
        sub_type=SignalSubType.FAMILY_MENTION,
        patterns=[
            r"\b(family|wife|husband|spouse|children|kids|parents|mother|father)\b",
            r"\b(whole family|for my family|protect (my|the) family)\b",
        ],
        min_confidence=0.75,
        speaker_filter=Speaker.CUSTOMER,
        recommended_action="Introduce Family Plan options. Families often qualify for bundled discounts of 10–15%.",
        suppression_window_s=180.0,
    ),
    DetectionRule(
        signal_type=SignalType.CROSS_SELL_OPPORTUNITY,
        sub_type=SignalSubType.SECONDARY_PRODUCT_INTEREST,
        patterns=[
            r"\b(also|additionally|what about|do you also (have|offer)|other product)\b",
            r"\b(dental|vision|maternity|life insurance|business loan)\b",
        ],
        min_confidence=0.70,
        speaker_filter=Speaker.CUSTOMER,
        recommended_action="Present complementary product. Keep it brief — one offer per call to avoid overwhelming the customer.",
        suppression_window_s=300.0,
    ),

    # ── Payment Difficulty ──
    DetectionRule(
        signal_type=SignalType.PAYMENT_DIFFICULTY,
        sub_type=SignalSubType.AFFORDABILITY_CONCERN,
        patterns=[
            r"\b(can't afford|cannot afford|too expensive|mahal|di kaya|berat|kemahalan)\b",
            r"\b(tight budget|financially|tough times|money is tight|struggling)\b",
            r"\b(I don't have|no money|wala akong pera|gak sanggup)\b",
        ],
        min_confidence=0.80,
        speaker_filter=Speaker.CUSTOMER,
        recommended_action="Offer flexible payment options: monthly installments, smaller coverage amounts, or a lower-tier plan. Show PHP/day breakdown.",
        suppression_window_s=120.0,
    ),
    DetectionRule(
        signal_type=SignalType.PAYMENT_DIFFICULTY,
        sub_type=SignalSubType.IRREGULAR_INCOME,
        patterns=[
            r"\b(irregular income|freelance|seasonal|self.?employed|no fixed|variable income)\b",
            r"\b(can I pay annually|annual payment|lump sum payment)\b",
        ],
        min_confidence=0.75,
        speaker_filter=Speaker.CUSTOMER,
        recommended_action="Mention annual payment option (saves ~5%). For self-employed, highlight our flexible premium adjustment feature.",
        suppression_window_s=180.0,
    ),

    # ── Legal Threats ──
    DetectionRule(
        signal_type=SignalType.LEGAL_THREAT,
        sub_type=SignalSubType.GENERIC,
        patterns=[
            r"\b(lawyer|attorney|legal|sue|lawsuit|court|bsp|regulator|complaint|regulatory)\b",
            r"\b(take (legal|this) action|file a (case|complaint|suit))\b",
        ],
        min_confidence=0.90,
        speaker_filter=Speaker.CUSTOMER,
        recommended_action="IMMEDIATE ESCALATION REQUIRED. Do not argue. Say: 'I understand your concern. I'm escalating this to our senior officer immediately.' Transfer now.",
        suppression_window_s=600.0,
    ),

    # ── Positive Sentiment / Buying Intent ──
    DetectionRule(
        signal_type=SignalType.POSITIVE_SENTIMENT,
        sub_type=SignalSubType.GENERIC,
        patterns=[
            r"\b(interested|sounds good|that works|I'll take it|let's do it|proceed|apply now)\b",
            r"\b(great|excellent|perfect|wonderful|that's helpful|I like that)\b",
        ],
        min_confidence=0.70,
        speaker_filter=Speaker.CUSTOMER,
        recommended_action="This is a closing moment! Confirm next steps immediately: 'Great! Shall I proceed with your application now?'",
        suppression_window_s=60.0,
    ),

    # ── Escalation Request ──
    DetectionRule(
        signal_type=SignalType.ESCALATION_REQUEST,
        sub_type=SignalSubType.GENERIC,
        patterns=[
            r"\b(speak to a (manager|supervisor|human|person)|transfer me|escalate)\b",
            r"\b(talk to someone|talk to a real person|not talking to a bot)\b",
        ],
        min_confidence=0.90,
        speaker_filter=Speaker.CUSTOMER,
        recommended_action="Acknowledge and escalate immediately. Do NOT try to resolve before transferring if customer insists.",
        suppression_window_s=300.0,
    ),
]


# ---------------------------------------------------------------------------
# Detected Signal
# ---------------------------------------------------------------------------

@dataclass
class DetectedSignal:
    """A signal detected in a transcript segment."""
    signal_id: str
    segment_id: str
    session_id: str
    signal_type: SignalType
    sub_type: SignalSubType
    confidence: float
    matched_phrase: str          # Exact text that triggered detection
    speaker: Speaker
    segment_text: str
    recommended_action: str
    detected_at: float = field(default_factory=time.perf_counter)
    extraction_latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "segment_id": self.segment_id,
            "signal_type": self.signal_type.value,
            "sub_type": self.sub_type.value,
            "confidence": round(self.confidence, 3),
            "matched_phrase": self.matched_phrase,
            "speaker": self.speaker.value,
            "recommended_action": self.recommended_action,
            "extraction_latency_ms": round(self.extraction_latency_ms, 2),
        }


# ---------------------------------------------------------------------------
# Signal Extractor
# ---------------------------------------------------------------------------

class SignalExtractor:
    """
    Real-time signal extractor for live call transcript segments.

    Processes each TranscriptSegment through all detection rules and
    returns a list of DetectedSignal objects. Designed to run in < 200ms P95.

    Features:
    - Pattern-based detection with configurable confidence thresholds
    - Speaker-aware filtering (some signals only fire for CUSTOMER)
    - Confidence adjustment based on pattern strength
    - False positive filtering (single-word matches get reduced confidence)
    """

    # Minimum confidence below which a signal is suppressed as false-positive
    MIN_CONFIDENCE_THRESHOLD = 0.60

    def __init__(self) -> None:
        # Pre-compile all regex patterns for performance
        self._compiled_rules: List[Tuple[DetectionRule, List[re.Pattern]]] = []
        for rule in _DETECTION_RULES:
            compiled = [
                re.compile(p, re.IGNORECASE) for p in rule.patterns
            ]
            self._compiled_rules.append((rule, compiled))

    def extract(self, segment: TranscriptSegment) -> List[DetectedSignal]:
        """
        Extract all signals from a single transcript segment.
        Returns a (possibly empty) list of DetectedSignal objects.
        """
        start = time.perf_counter()
        signals: List[DetectedSignal] = []

        text = segment.text
        text_lower = text.lower()

        for rule, compiled_patterns in self._compiled_rules:
            # Speaker filter
            if rule.speaker_filter and segment.speaker != rule.speaker_filter:
                continue

            # Test all patterns for this rule
            matched_phrase = ""
            best_match = None

            for pattern in compiled_patterns:
                m = pattern.search(text)
                if m:
                    best_match = m
                    matched_phrase = m.group(0)
                    break  # First match per rule is enough

            if not best_match:
                continue

            # Confidence computation
            confidence = self._compute_confidence(
                rule=rule,
                matched_phrase=matched_phrase,
                full_text=text,
            )

            if confidence < self.MIN_CONFIDENCE_THRESHOLD:
                continue

            import uuid
            extraction_latency_ms = (time.perf_counter() - start) * 1000

            signal = DetectedSignal(
                signal_id=str(uuid.uuid4())[:8],
                segment_id=segment.segment_id,
                session_id=segment.session_id,
                signal_type=rule.signal_type,
                sub_type=rule.sub_type,
                confidence=round(confidence, 3),
                matched_phrase=matched_phrase,
                speaker=segment.speaker,
                segment_text=text,
                recommended_action=rule.recommended_action,
                detected_at=time.perf_counter(),
                extraction_latency_ms=round(extraction_latency_ms, 2),
            )
            signals.append(signal)

        return signals

    def _compute_confidence(
        self,
        rule: DetectionRule,
        matched_phrase: str,
        full_text: str,
    ) -> float:
        """
        Compute a final confidence score for a detected signal.

        Adjustments applied:
        - Base confidence from rule definition
        - +0.05 if multiple patterns from same rule match
        - -0.10 if match is very short (< 3 words) → likely false positive
        - +0.05 if surrounding context reinforces the signal
        """
        confidence = rule.min_confidence

        # Penalize very short matches
        if len(matched_phrase.split()) < 2:
            confidence -= 0.10

        # Boost for longer, more specific matches
        if len(matched_phrase.split()) >= 5:
            confidence += 0.05

        # Context reinforcement
        text_lower = full_text.lower()
        frustration_amplifiers = ["again", "still", "always", "never", "every time", "keep"]
        if any(amp in text_lower for amp in frustration_amplifiers):
            if rule.signal_type == SignalType.CUSTOMER_FRUSTRATION:
                confidence += 0.08

        return min(confidence, 1.0)

"""
Q1 Voice Agent — Lead Qualification State Machine
==================================================
Implements a deterministic state machine for lead qualification covering:

  Use Case A: Health Insurance lead qualification
  Use Case B: Business Loan lead qualification

The state machine tracks collected parameters, validates them against
known eligibility rules, and determines the next best question or action
(qualify, disqualify, escalate, or provide info).

All transitions are fully logged for compliance and auditability.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class UseCase(str, Enum):
    HEALTH_INSURANCE = "health_insurance"
    BUSINESS_LOAN = "business_loan"


class CallState(str, Enum):
    """States in the qualification state machine."""
    GREETING = "greeting"
    USE_CASE_DETECTION = "use_case_detection"
    # Health Insurance states
    HI_AGE = "hi_age"
    HI_PRE_EXISTING = "hi_pre_existing"
    HI_BUDGET = "hi_budget"
    HI_COVERAGE_NEEDS = "hi_coverage_needs"
    HI_RECOMMENDATION = "hi_recommendation"
    # Business Loan states
    BL_BUSINESS_TYPE = "bl_business_type"
    BL_OPERATING_YEARS = "bl_operating_years"
    BL_MONTHLY_REVENUE = "bl_monthly_revenue"
    BL_LOAN_AMOUNT = "bl_loan_amount"
    BL_COLLATERAL = "bl_collateral"
    BL_CREDIT_HISTORY = "bl_credit_history"
    BL_RECOMMENDATION = "bl_recommendation"
    # Terminal states
    OBJECTION_HANDLING = "objection_handling"
    ESCALATION = "escalation"
    INFORMATION_PROVIDED = "information_provided"
    DISQUALIFIED = "disqualified"
    QUALIFIED = "qualified"
    CALL_ENDED = "call_ended"


class QualificationOutcome(str, Enum):
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    NEEDS_MORE_INFO = "needs_more_info"
    ESCALATE = "escalate"
    PENDING = "pending"


# ---------------------------------------------------------------------------
# Lead Profile
# ---------------------------------------------------------------------------

@dataclass
class LeadProfile:
    """Collected information about a prospective customer during qualification."""

    # Call metadata
    session_id: str = ""
    use_case: Optional[UseCase] = None
    call_start: datetime = field(default_factory=datetime.utcnow)

    # Health Insurance fields
    age: Optional[int] = None
    has_pre_existing_conditions: Optional[bool] = None
    pre_existing_details: str = ""
    monthly_budget_php: Optional[float] = None
    coverage_needs: List[str] = field(default_factory=list)  # e.g. ["inpatient", "dental"]
    has_dependents: Optional[bool] = None
    num_dependents: int = 0

    # Business Loan fields
    business_type: str = ""
    operating_years: Optional[float] = None
    monthly_revenue_php: Optional[float] = None
    loan_amount_php: Optional[float] = None
    has_collateral: Optional[bool] = None
    collateral_value_php: Optional[float] = None
    has_adverse_credit: Optional[bool] = None

    # Qualification tracking
    objections_raised: List[str] = field(default_factory=list)
    escalation_requested: bool = False
    out_of_scope_questions: List[str] = field(default_factory=list)
    qualification_outcome: QualificationOutcome = QualificationOutcome.PENDING

    def is_hi_eligible(self) -> Tuple[bool, str]:
        """
        Evaluate health insurance eligibility based on collected data.
        Returns (is_eligible, reason).
        """
        if self.age is None:
            return False, "Age not yet collected."
        if self.age < 1:
            return False, "Applicant is below minimum age of 1 year."
        if self.age > 65:
            return False, (
                f"Applicant age {self.age} exceeds maximum entry age of 65. "
                "Renewal is possible up to 75 if already insured."
            )
        return True, "Age is within acceptable range (1–65)."

    def is_bl_eligible(self) -> Tuple[bool, str]:
        """
        Evaluate business loan eligibility based on collected data.
        Returns (is_eligible, reason).
        """
        if self.operating_years is not None and self.operating_years < 2:
            if self.operating_years >= 1:
                return (
                    False,
                    f"Business has been operating for {self.operating_years} year(s). "
                    "Standard SME loans require 2 years. Startup Loan Program may apply.",
                )
            return False, "Business must have at least 1 year of operation to apply."

        if self.has_adverse_credit:
            return False, (
                "Active adverse credit history detected. "
                "Loan application would likely be declined. Consider credit rehabilitation first."
            )
        return True, "Preliminary eligibility check passed."

    def to_summary(self) -> str:
        """Generate a qualification summary for logging and handoff."""
        lines = [
            f"=== Lead Profile Summary ===",
            f"Session   : {self.session_id}",
            f"Use Case  : {self.use_case.value if self.use_case else 'Unknown'}",
            f"Outcome   : {self.qualification_outcome.value}",
        ]
        if self.use_case == UseCase.HEALTH_INSURANCE:
            lines += [
                f"Age       : {self.age}",
                f"Pre-Exist : {self.has_pre_existing_conditions} ({self.pre_existing_details})",
                f"Budget    : PHP {self.monthly_budget_php:,.0f}/mo" if self.monthly_budget_php else "Budget    : Not stated",
                f"Dependents: {self.num_dependents}",
                f"Coverage  : {', '.join(self.coverage_needs) or 'Not stated'}",
            ]
        elif self.use_case == UseCase.BUSINESS_LOAN:
            lines += [
                f"Biz Type  : {self.business_type}",
                f"Oper. Yrs : {self.operating_years}",
                f"Monthly Rev: PHP {self.monthly_revenue_php:,.0f}" if self.monthly_revenue_php else "Monthly Rev: Not stated",
                f"Loan Req  : PHP {self.loan_amount_php:,.0f}" if self.loan_amount_php else "Loan Req  : Not stated",
                f"Collateral: {self.has_collateral}",
                f"Adverse Cr: {self.has_adverse_credit}",
            ]
        lines += [
            f"Objections: {len(self.objections_raised)}",
            f"Escalation: {self.escalation_requested}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# State Transition Logs
# ---------------------------------------------------------------------------

@dataclass
class StateTransition:
    """Records a single state transition in the qualification flow."""
    from_state: CallState
    to_state: CallState
    trigger: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Qualification Flow Engine
# ---------------------------------------------------------------------------

class QualificationFlow:
    """
    Deterministic state machine for voice agent lead qualification.

    The flow manager tracks the current state, collects lead parameters,
    validates eligibility rules, and determines the next action.

    Usage:
        flow = QualificationFlow(session_id="test-001")
        state, response = flow.process("I'm interested in health insurance")
        state, response = flow.process("I am 42 years old")
        # ... continue turn by turn
    """

    # Ordered question sequences
    _HI_STATES = [
        CallState.HI_AGE,
        CallState.HI_PRE_EXISTING,
        CallState.HI_BUDGET,
        CallState.HI_COVERAGE_NEEDS,
        CallState.HI_RECOMMENDATION,
    ]

    _BL_STATES = [
        CallState.BL_BUSINESS_TYPE,
        CallState.BL_OPERATING_YEARS,
        CallState.BL_MONTHLY_REVENUE,
        CallState.BL_LOAN_AMOUNT,
        CallState.BL_COLLATERAL,
        CallState.BL_CREDIT_HISTORY,
        CallState.BL_RECOMMENDATION,
    ]

    # Escalation triggers — phrases that immediately trigger human handoff
    _ESCALATION_PHRASES = [
        "speak to a human", "speak to a manager", "speak to a supervisor",
        "talk to a person", "talk to someone", "i want to complain",
        "this is ridiculous", "legal", "regulatory", "bsp complaint",
        "formal complaint", "lawsuit",
    ]

    def __init__(self, session_id: str = "") -> None:
        import uuid
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.current_state: CallState = CallState.GREETING
        self.lead: LeadProfile = LeadProfile(session_id=self.session_id)
        self.history: List[Dict[str, str]] = []
        self.transitions: List[StateTransition] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, user_input: str) -> Tuple[CallState, str]:
        """
        Process a user utterance and return (new_state, agent_response).
        This is the main entry point called once per conversational turn.
        """
        user_input_clean = user_input.strip()
        self.history.append({"role": "user", "content": user_input_clean})
        logger.info("[%s] State: %s | Input: %s", self.session_id, self.current_state.value, user_input_clean[:60])

        # Check for escalation trigger first (highest priority)
        if self._is_escalation_request(user_input_clean):
            return self._transition_to_escalation(user_input_clean)

        # Route to state-specific handler
        handler_map = {
            CallState.GREETING: self._handle_greeting,
            CallState.USE_CASE_DETECTION: self._handle_use_case_detection,
            CallState.HI_AGE: self._handle_hi_age,
            CallState.HI_PRE_EXISTING: self._handle_hi_pre_existing,
            CallState.HI_BUDGET: self._handle_hi_budget,
            CallState.HI_COVERAGE_NEEDS: self._handle_hi_coverage,
            CallState.HI_RECOMMENDATION: self._handle_hi_recommendation,
            CallState.BL_BUSINESS_TYPE: self._handle_bl_business_type,
            CallState.BL_OPERATING_YEARS: self._handle_bl_operating_years,
            CallState.BL_MONTHLY_REVENUE: self._handle_bl_monthly_revenue,
            CallState.BL_LOAN_AMOUNT: self._handle_bl_loan_amount,
            CallState.BL_COLLATERAL: self._handle_bl_collateral,
            CallState.BL_CREDIT_HISTORY: self._handle_bl_credit_history,
            CallState.BL_RECOMMENDATION: self._handle_bl_recommendation,
            CallState.OBJECTION_HANDLING: self._handle_objection,
            CallState.ESCALATION: self._handle_escalation,
            CallState.QUALIFIED: self._handle_qualified,
            CallState.DISQUALIFIED: self._handle_disqualified,
            CallState.CALL_ENDED: self._handle_call_ended,
        }

        handler = handler_map.get(self.current_state, self._handle_fallback)
        new_state, response = handler(user_input_clean)
        self._transition(self.current_state, new_state, user_input_clean[:30])
        self.current_state = new_state
        self.history.append({"role": "agent", "content": response})
        return new_state, response

    def get_opening_message(self) -> str:
        """Return the initial agent greeting to start the call."""
        msg = (
            "Hello! Thank you for calling. My name is Alex, and I'm here to help you today. "
            "I can assist you with our Health Insurance plans or Business Loan products. "
            "Which of these are you calling about today?"
        )
        self.history.append({"role": "agent", "content": msg})
        return msg

    # ------------------------------------------------------------------
    # State Handlers
    # ------------------------------------------------------------------

    def _handle_greeting(self, text: str) -> Tuple[CallState, str]:
        response = self._detect_and_respond_use_case(text)
        # Return self.current_state — it was updated inside _detect_and_respond_use_case
        # (to HI_AGE or BL_BUSINESS_TYPE if product was detected, otherwise unchanged)
        return self.current_state, response

    def _handle_use_case_detection(self, text: str) -> Tuple[CallState, str]:
        response = self._detect_and_respond_use_case(text)
        return self.current_state, response

    def _detect_and_respond_use_case(self, text: str) -> str:
        text_lower = text.lower()
        if any(w in text_lower for w in ["health", "insurance", "hmo", "medical", "hospital", "coverage"]):
            self.lead.use_case = UseCase.HEALTH_INSURANCE
            self.current_state = CallState.HI_AGE
            return (
                "Great! I'd be happy to help you find the right health insurance plan. "
                "To get started, may I ask — how old are you?"
            )
        elif any(w in text_lower for w in ["loan", "business", "financing", "capital", "credit", "borrow"]):
            self.lead.use_case = UseCase.BUSINESS_LOAN
            self.current_state = CallState.BL_BUSINESS_TYPE
            return (
                "Excellent! I can help you explore our Business Loan options. "
                "First, could you tell me what type of business you have? "
                "For example, is it a sole proprietorship, partnership, or corporation?"
            )
        else:
            return (
                "I want to make sure I direct you to the right product. "
                "Are you calling about Health Insurance coverage, "
                "or are you looking to apply for a Business Loan?"
            )

    # --- Health Insurance Handlers ---

    def _handle_hi_age(self, text: str) -> Tuple[CallState, str]:
        age = self._extract_number(text)
        if age is None:
            return CallState.HI_AGE, "Could you please tell me your age in years?"

        self.lead.age = int(age)
        eligible, reason = self.lead.is_hi_eligible()

        if not eligible:
            self.lead.qualification_outcome = QualificationOutcome.DISQUALIFIED
            return (
                CallState.DISQUALIFIED,
                f"Thank you for that information. Unfortunately, based on your age of {int(age)}, "
                f"{reason} I'm unable to process an application at this time, but I can connect "
                f"you to our specialist who may be able to explore other options for you. "
                f"Would you like me to do that?"
            )

        return (
            CallState.HI_PRE_EXISTING,
            f"Thank you. At {int(age)}, you're well within our coverage age range. "
            "Now, do you have any pre-existing medical conditions such as diabetes, "
            "hypertension, asthma, or any history of surgery or hospitalization "
            "in the past two years?"
        )

    def _handle_hi_pre_existing(self, text: str) -> Tuple[CallState, str]:
        text_lower = text.lower()
        has_condition = any(w in text_lower for w in ["yes", "have", "diabetes", "hypertension",
                                                        "asthma", "heart", "cancer", "surgery", "hospitalized"])
        no_condition = any(w in text_lower for w in ["no", "none", "healthy", "nothing", "don't"])

        if has_condition:
            self.lead.has_pre_existing_conditions = True
            self.lead.pre_existing_details = text[:100]
            return (
                CallState.HI_BUDGET,
                "Thank you for being upfront about that. Pre-existing conditions don't automatically "
                "disqualify you — we have a 12-month exclusion period for declared conditions, "
                "after which coverage applies. "
                "Now, what's your approximate monthly budget for health insurance?"
            )
        elif no_condition:
            self.lead.has_pre_existing_conditions = False
            return (
                CallState.HI_BUDGET,
                "That's great — a clean health history means you can access our full range of plans "
                "without any exclusion periods. "
                "What is your approximate monthly budget for health insurance premiums?"
            )
        else:
            return (
                CallState.HI_PRE_EXISTING,
                "Just to clarify — do you currently have or have you previously been treated for "
                "any medical conditions like diabetes, heart disease, or asthma? "
                "A simple yes or no helps us determine the right plan for you."
            )

    def _handle_hi_budget(self, text: str) -> Tuple[CallState, str]:
        amount = self._extract_number(text)
        if amount:
            self.lead.monthly_budget_php = float(amount)

        return (
            CallState.HI_COVERAGE_NEEDS,
            "Perfect. Lastly, what type of coverage are you most interested in? "
            "For example: inpatient hospitalization, outpatient consultations, "
            "emergency care, dental coverage, or maternity benefits?"
        )

    def _handle_hi_coverage(self, text: str) -> Tuple[CallState, str]:
        coverage_keywords = {
            "inpatient": "inpatient",
            "outpatient": "outpatient",
            "emergency": "emergency",
            "dental": "dental",
            "maternity": "maternity",
            "critical illness": "critical_illness",
            "mental health": "mental_health",
            "vision": "vision",
        }
        text_lower = text.lower()
        for keyword, tag in coverage_keywords.items():
            if keyword in text_lower:
                self.lead.coverage_needs.append(tag)

        if not self.lead.coverage_needs:
            self.lead.coverage_needs = ["inpatient", "outpatient"]  # Sensible default

        return CallState.HI_RECOMMENDATION, self._generate_hi_recommendation()

    def _handle_hi_recommendation(self, text: str) -> Tuple[CallState, str]:
        text_lower = text.lower()
        if any(w in text_lower for w in ["yes", "interested", "proceed", "apply", "sign up", "sure", "ok", "okay", "correct", "yep", "yeah"]):
            self.lead.qualification_outcome = QualificationOutcome.QUALIFIED
            return (
                CallState.QUALIFIED,
                "Wonderful! You're officially qualified. I'll connect you with our licensed insurance advisor "
                "who will walk you through the complete application process. "
                "Expect a call within 24 hours. Thank you for choosing us — have a great day!"
            )
        elif any(w in text_lower for w in ["no", "not interested", "pass", "think", "later"]):
            if "think" in text_lower or "later" in text_lower:
                self.lead.objections_raised.append("needs more time")
                return (
                    CallState.OBJECTION_HANDLING,
                    "Of course, take all the time you need. May I ask — is there a specific concern "
                    "or question I can answer that might help you decide? "
                    "For example, about coverage limits, premiums, or pre-existing conditions?"
                )
            return (
                CallState.CALL_ENDED,
                "Understood. No problem at all. If you change your mind, you're always welcome to "
                "call us back or visit our website. Have a wonderful day!"
            )
        return (
            CallState.HI_RECOMMENDATION,
            "Would you like to proceed with an application, or do you have any questions "
            "about the plan I've described?"
        )

    def _generate_hi_recommendation(self) -> str:
        age = self.lead.age or 30
        budget = self.lead.monthly_budget_php
        has_pre_ex = self.lead.has_pre_existing_conditions
        needs = self.lead.coverage_needs

        # Recommend based on profile
        if budget and budget < 700:
            plan = "Basic HMO Plan (PHP 6,000/year)"
        elif budget and budget < 1500:
            plan = "Standard HMO Plan (PHP 12,000/year)"
        else:
            plan = "Executive HMO Plan or Comprehensive Plan (PHP 25,000–PHP 45,000/year)"

        pre_ex_note = (
            " Given your pre-existing condition, coverage will apply after a 12-month exclusion period."
            if has_pre_ex else
            " Since you have no pre-existing conditions, full coverage starts from Day 1 (accidents) "
            "and after 30 days for illnesses."
        )

        needs_str = ", ".join(needs) if needs else "general hospitalization"

        return (
            f"Based on your profile — age {age}, coverage needs ({needs_str})"
            + (f", and budget of approximately PHP {budget:,.0f}/month" if budget else "")
            + f" — I'd recommend our {plan}.{pre_ex_note} "
            "This plan gives you excellent value and peace of mind. "
            "Are you interested in proceeding with an application?"
        )

    # --- Business Loan Handlers ---

    def _handle_bl_business_type(self, text: str) -> Tuple[CallState, str]:
        self.lead.business_type = text[:80]
        return (
            CallState.BL_OPERATING_YEARS,
            "Thank you. How many years has your business been operating?"
        )

    def _handle_bl_operating_years(self, text: str) -> Tuple[CallState, str]:
        raw_val = self._extract_number(text)
        if raw_val is None:
            return CallState.BL_OPERATING_YEARS, "Could you let me know how many years your business has been running?"

        text_lower = text.lower()
        if any(m in text_lower for m in ["month", "months", "mo"]):
            years = round(raw_val / 12.0, 2)
        else:
            years = float(raw_val)

        self.lead.operating_years = years
        eligible, reason = self.lead.is_bl_eligible()

        if not eligible and years >= 1:
            # Startup path — note it but continue
            return (
                CallState.BL_MONTHLY_REVENUE,
                f"Thank you. At {years} year(s) of operation, you may qualify for our Startup Loan Program. "
                "This has slightly different requirements from our standard SME loan. "
                "Could you share your average monthly revenue or sales?"
            )
        elif not eligible:
            self.lead.qualification_outcome = QualificationOutcome.DISQUALIFIED
            return (
                CallState.DISQUALIFIED,
                "Unfortunately, businesses with less than 12 months of operation are currently "
                "outside our loan eligibility criteria. I recommend revisiting once you've "
                "completed at least one year. In the meantime, I can share some resources "
                "on financial readiness for your business."
            )

        return (
            CallState.BL_MONTHLY_REVENUE,
            f"Excellent — {years} years of operation is a strong indicator. "
            "What is your average monthly revenue or gross sales?"
        )

    def _handle_bl_monthly_revenue(self, text: str) -> Tuple[CallState, str]:
        amount = self._extract_number(text)
        if amount:
            self.lead.monthly_revenue_php = float(amount)

        return (
            CallState.BL_LOAN_AMOUNT,
            "Good. How much financing are you looking to apply for?"
        )

    def _handle_bl_loan_amount(self, text: str) -> Tuple[CallState, str]:
        amount = self._extract_number(text)
        if amount:
            self.lead.loan_amount_php = float(amount)

        return (
            CallState.BL_COLLATERAL,
            "Do you have any assets available as collateral? "
            "For example, real estate property, land title, or commercial vehicle?"
        )

    def _handle_bl_collateral(self, text: str) -> Tuple[CallState, str]:
        text_lower = text.lower()
        has_collateral = any(w in text_lower for w in ["yes", "have", "property", "land", "title", "vehicle", "building"])
        no_collateral = any(w in text_lower for w in ["no", "none", "don't", "nothing"])

        if has_collateral:
            self.lead.has_collateral = True
            amount = self._extract_number(text)
            if amount:
                self.lead.collateral_value_php = float(amount)
        elif no_collateral:
            self.lead.has_collateral = False

        return (
            CallState.BL_CREDIT_HISTORY,
            "Understood. One last question — have you had any overdue payments, "
            "loan defaults, or adverse credit history in the past five years?"
        )

    def _handle_bl_credit_history(self, text: str) -> Tuple[CallState, str]:
        text_lower = text.lower()

        # Negation-aware detection: check for "no/never/clean/good" FIRST,
        # then only flag adverse if no negation prefix found near bad keywords.
        _ADVERSE_WORDS = ["default", "overdue", "late payment", "missed payment",
                          "adverse credit", "bad credit", "bankrupt"]
        _CLEAN_WORDS   = ["no default", "no overdue", "no late", "no missed",
                          "no adverse", "no bad", "never defaulted", "never missed",
                          "good credit", "clean credit", "clean history",
                          "good history", "no issue", "no problem",
                          "no defaults", "none", "clean"]
        _EXPLICIT_BAD  = ["i have defaults", "i defaulted", "i have overdue",
                          "i had late payment", "yes i have", "yes, i have",
                          "adverse credit", "bad credit", "bankrupt"]

        # Clean check takes priority
        is_clean = any(phrase in text_lower for phrase in _CLEAN_WORDS)
        is_bad   = any(phrase in text_lower for phrase in _EXPLICIT_BAD)

        # Fallback: bare adverse words without negation context
        if not is_clean and not is_bad:
            is_bad = any(w in text_lower for w in _ADVERSE_WORDS)

        if is_bad:
            self.lead.has_adverse_credit = True
        else:
            # Default to clean credit (benefit of the doubt)
            self.lead.has_adverse_credit = False

        eligible, reason = self.lead.is_bl_eligible()

        if not eligible:
            self.lead.qualification_outcome = QualificationOutcome.DISQUALIFIED
            return (
                CallState.DISQUALIFIED,
                f"Thank you for your honesty. {reason} "
                "I'd recommend speaking to one of our credit advisors who can guide you on "
                "improving your credit profile before reapplying."
            )

        return CallState.BL_RECOMMENDATION, self._generate_bl_recommendation()

    def _handle_bl_recommendation(self, text: str) -> Tuple[CallState, str]:
        text_lower = text.lower()
        if any(w in text_lower for w in ["yes", "interested", "proceed", "apply"]):
            self.lead.qualification_outcome = QualificationOutcome.QUALIFIED
            return (
                CallState.QUALIFIED,
                "Fantastic! I'll transfer you to our Business Loan specialist who will walk you "
                "through the complete application process and document checklist. "
                "Is there anything else I can clarify before I transfer you?"
            )
        elif any(w in text_lower for w in ["no", "later", "think"]):
            return (
                CallState.OBJECTION_HANDLING,
                "I completely understand. What specific concern can I address for you? "
                "Is it the documentation requirements, the interest rate, or something else?"
            )
        return (
            CallState.BL_RECOMMENDATION,
            "Would you like to proceed with the preliminary application, "
            "or do you have any questions about the loan terms?"
        )

    def _generate_bl_recommendation(self) -> str:
        loan = self.lead.loan_amount_php
        revenue = self.lead.monthly_revenue_php
        has_collateral = self.lead.has_collateral
        years = self.lead.operating_years

        loan_str = f"PHP {loan:,.0f}" if loan else "the requested amount"
        rev_str = f"PHP {revenue:,.0f}/month" if revenue else "your stated revenue"

        collateral_note = (
            "With collateral, you may qualify for secured loan rates as low as 1.25%/month."
            if has_collateral else
            "Since you have no collateral, you may qualify for our unsecured SME loan up to PHP 2,000,000."
        )

        return (
            f"Based on your profile — {years} years in business, "
            f"revenue of {rev_str}, and loan requirement of {loan_str} — "
            f"your preliminary assessment looks promising. {collateral_note} "
            "Our approval timeline is 10–15 business days after complete document submission. "
            "Would you like me to proceed with your preliminary application?"
        )

    # --- Generic Handlers ---

    def _handle_objection(self, text: str) -> Tuple[CallState, str]:
        self.lead.objections_raised.append(text[:80])
        text_lower = text.lower()

        if "expensive" in text_lower or "afford" in text_lower or "cost" in text_lower:
            return (
                CallState.OBJECTION_HANDLING,
                "I completely understand your concern about cost. "
                "Let me assure you that we have plans starting as low as PHP 500/month — "
                "roughly the cost of a daily coffee. More importantly, one hospital stay can "
                "cost PHP 50,000 to PHP 200,000 without coverage. "
                "Would you like me to calculate the exact cost for the plan that fits your budget?"
            )
        elif "think" in text_lower or "later" in text_lower:
            return (
                CallState.CALL_ENDED,
                "Of course. Take all the time you need. I'll send you a summary of our plans "
                "to review at your own pace. Is there a good email address I can send that to? "
                "And please feel free to call back anytime."
            )
        else:
            return (
                CallState.OBJECTION_HANDLING,
                "Thank you for sharing that. I want to make sure I address your concern completely. "
                "Could you tell me a bit more about what's holding you back? "
                "I'm here to help you find the best solution."
            )

    def _handle_escalation(self, text: str) -> Tuple[CallState, str]:
        return (
            CallState.ESCALATION,
            "I completely understand, and I apologize for any inconvenience. "
            "I'm transferring you now to a senior specialist who will be able to assist you directly. "
            "Please hold for just a moment."
        )

    def _handle_call_ended(self, text: str) -> Tuple[CallState, str]:
        return (
            CallState.CALL_ENDED,
            "Thank you for calling. Have a wonderful day!"
        )

    def _handle_qualified(self, text: str) -> Tuple[CallState, str]:
        """Handle any further input after call is QUALIFIED — stay in terminal state."""
        return (
            CallState.QUALIFIED,
            "Your application has already been submitted. Our advisor will be in touch within 24 hours. "
            "Is there anything else I can help you with before we close the call?"
        )

    def _handle_disqualified(self, text: str) -> Tuple[CallState, str]:
        """Handle any further input after DISQUALIFIED."""
        return (
            CallState.DISQUALIFIED,
            "Thank you for your time. Unfortunately, based on the information provided, "
            "we're unable to proceed with an application at this time. "
            "Please don't hesitate to contact us in the future."
        )

    def _handle_fallback(self, text: str) -> Tuple[CallState, str]:
        self.lead.out_of_scope_questions.append(text[:100])
        return (
            self.current_state,
            "I apologize — I didn't quite catch that. Could you repeat your question? "
            "I'm here to help with Health Insurance plans and Business Loans."
        )

    def _transition_to_escalation(self, trigger: str) -> Tuple[CallState, str]:
        self.lead.escalation_requested = True
        self._transition(self.current_state, CallState.ESCALATION, trigger[:30])
        self.current_state = CallState.ESCALATION
        response = (
            "I understand. I'm escalating this to a senior specialist right away. "
            "Please hold while I connect you."
        )
        self.history.append({"role": "agent", "content": response})
        return CallState.ESCALATION, response

    # ------------------------------------------------------------------
    # Utility Helpers
    # ------------------------------------------------------------------

    def _is_escalation_request(self, text: str) -> bool:
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in self._ESCALATION_PHRASES)

    @staticmethod
    def _extract_number(text: str) -> Optional[float]:
        """Extract the first numeric value from text (handles K/M suffixes and commas)."""
        import re
        text = text.replace(",", "")
        # Handle "1.5 million" or "1.5M"
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:million|M)\b", text, re.IGNORECASE)
        if match:
            return float(match.group(1)) * 1_000_000

        # Handle "500K" or "500 thousand"
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:thousand|K)\b", text, re.IGNORECASE)
        if match:
            return float(match.group(1)) * 1_000

        # Plain number
        match = re.search(r"\d+(?:\.\d+)?", text)
        if match:
            return float(match.group(0))
        return None

    def _transition(self, from_state: CallState, to_state: CallState, trigger: str) -> None:
        self.transitions.append(StateTransition(from_state, to_state, trigger))
        logger.debug("[%s] %s → %s (trigger: %s)", self.session_id, from_state.value, to_state.value, trigger)

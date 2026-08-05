"""
Q3 Multilingual — Philippines Insurance Bot (Taglish)
======================================================
A life insurance and bancassurance voice bot for the Philippine market.

Language Profile:
- Primary: Filipino/Tagalog mixed with English (Taglish)
- Respect markers: Always uses "po" and "opo" with customers
- Tone: Warm, patient, family-oriented — Filipinos respond well to
  relationship-building before product pitching

Local Finance Terms Used:
  premium / hulog — payment for insurance
  policy / polisa — insurance contract
  beneficiary / benepisyaryo — person who receives payout
  rider — optional benefit add-on
  lapse — policy going inactive due to missed payment
  coverage / saklaw — what the insurance protects
  face amount — sum assured / death benefit
  surrender — cancelling and cashing out a policy

Cultural Context:
- Filipino families often purchase insurance for OFW (Overseas Filipino Worker) protection
- "Bayanihan" spirit: insurance framed as protecting the family, not just the individual
- Customers prefer "hulog" over "premium" in informal contexts
- Respect markers (po/opo) are non-negotiable for trust-building
"""

from __future__ import annotations

import sys
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from q3_multilingual.localization_engine import (
    Language,
    LocalizationEngine,
    PH_INSURANCE_LEXICON,
    PH_RESPECT_MARKERS,
)


# ---------------------------------------------------------------------------
# Bot State
# ---------------------------------------------------------------------------

class PHBotState(str, Enum):
    GREETING = "greeting"
    NEEDS_ASSESSMENT = "needs_assessment"
    PRODUCT_PRESENTATION = "product_presentation"
    BENEFICIARY = "beneficiary"
    PREMIUM_DISCUSSION = "premium_discussion"
    OBJECTION = "objection"
    APPLICATION = "application"
    ESCALATION = "escalation"
    CLOSING = "closing"


# ---------------------------------------------------------------------------
# Script Library (Taglish)
# ---------------------------------------------------------------------------

# Each entry: (English version, Taglish version)
TAGLISH_SCRIPTS: Dict[str, Tuple[str, str]] = {
    "greeting": (
        "Good day! Thank you for calling. I'm here to help you with our life insurance and health insurance products. How may I assist you today?",
        "Magandang araw po! Salamat sa inyong pagtawag. Nandito po ako para tulungan kayo sa aming life insurance at health insurance. Paano ko po kayo matutulungan ngayon?",
    ),
    "ask_name": (
        "May I know your name, please?",
        "Pwede po ba ninyong ibahagi ang inyong pangalan?",
    ),
    "ask_age": (
        "How old are you, if you don't mind me asking?",
        "Puwede ko po bang malaman ang inyong edad?",
    ),
    "ask_family": (
        "Do you have a spouse or children you'd like to protect with insurance?",
        "Mayroon po ba kayong asawa o mga anak na gustong protektahan sa pamamagitan ng insurance?",
    ),
    "ask_ofw": (
        "Are you or any family member currently working abroad?",
        "Kayo po ba o may kapamilya na nagtatrabaho sa ibang bansa?",
    ),
    "ask_coverage": (
        "What type of coverage are you most interested in — life insurance, health insurance, or both?",
        "Anong uri po ng coverage ang mas interesado kayo — life insurance, health insurance, o pareho?",
    ),
    "present_life": (
        "Our Life Insurance plan provides a lump-sum payment to your beneficiary in case of death or total disability. "
        "You can choose coverage amounts from PHP 500,000 up to PHP 5,000,000.",
        "Ang aming Life Insurance plan po ay nagbibigay ng lump-sum na bayad sa inyong beneficiary "
        "o benepisyaryo kung sakali mang mamatay o maging may kapansanan. "
        "Puwede kayong pumili ng face amount mula PHP 500,000 hanggang PHP 5,000,000 po.",
    ),
    "explain_premium": (
        "Your monthly premium depends on your age and coverage amount. "
        "For example, a PHP 1,000,000 coverage for a 35-year-old is approximately PHP 1,200 per month.",
        "Ang inyong buwanang hulog o premium po ay depende sa inyong edad at sa halaga ng coverage. "
        "Halimbawa po, ang PHP 1,000,000 na coverage para sa isang 35 taong gulang ay humigit-kumulang "
        "PHP 1,200 bawat buwan po.",
    ),
    "explain_beneficiary": (
        "Your beneficiary is the person who will receive the insurance payout when your policy matures or in the event of your passing.",
        "Ang inyong beneficiary o benepisyaryo po ang taong makakatanggap ng pera mula sa inyong policy "
        "kapag ito ay na-mature na o sakaling kayo ay mawala.",
    ),
    "explain_rider": (
        "We also offer optional riders — these are additional benefits you can add to your policy, "
        "such as a Critical Illness Rider or an Accidental Death Benefit.",
        "Mayroon din po kaming tinatawag na rider — ito po ay mga karagdagang benepisyo na maaari ninyong "
        "idagdag sa inyong policy, tulad ng Critical Illness Rider o Accidental Death Benefit po.",
    ),
    "explain_lapse": (
        "A policy lapse happens when premiums are not paid for a certain period. "
        "If your policy lapses, coverage is suspended. We have a grace period of 30 days for missed payments.",
        "Ang lapse po ay nangyayari kapag hindi nabayaran ang premium sa loob ng ilang panahon. "
        "Kung mag-lapse po ang inyong policy, ang coverage ay magiging suspend muna. "
        "Mayroon po kaming 30-day grace period para sa mga napalampas na hulog.",
    ),
    "objection_expensive": (
        "I completely understand your concern, po. "
        "Think of it this way — for just PHP 40 a day, your family is fully protected. "
        "That's less than the cost of your daily coffee or merienda. "
        "Isn't your family's future worth that?",
        "Naiintindihan ko po ang inyong alalahanin. "
        "Isipin lang po natin ito — para lamang sa PHP 40 bawat araw, "
        "ang inyong pamilya ay ganap na poprotektahan. "
        "Mas mura pa po ito kaysa sa inyong araw-araw na kape o merienda. "
        "Hindi ba po sulit ang kinabukasan ng inyong pamilya?",
    ),
    "objection_think": (
        "Of course, po — take all the time you need. "
        "May I ask, is there anything specific you'd like to think about? "
        "I'd like to make sure you have all the information before you decide.",
        "Sige lang po — huwag kayong mag-alala, pag-isipan muna ninyo. "
        "Puwede ko po bang malaman kung may specific na bagay na gusto ninyong pag-aralan? "
        "Gusto ko pong matiyak na kumpleto ang inyong impormasyon bago kayo magdesisyon.",
    ),
    "objection_pre_existing": (
        "Thank you for being open about that, po. Having a pre-existing condition doesn't automatically "
        "disqualify you. Depending on the condition, we may be able to offer coverage with a 12-month "
        "exclusion period, after which full coverage applies.",
        "Salamat po sa inyong pagiging bukas tungkol doon. "
        "Ang pagkakaroon ng pre-existing condition ay hindi agad nangangahulugang hindi kayo maaaring "
        "ma-insure. Depende po sa kondisyon, maaari pa rin kaming mag-alok ng coverage "
        "na may 12-buwang exclusion period — pagkatapos nito, ganap na ang inyong coverage po.",
    ),
    "ask_proceed": (
        "Based on everything we discussed, would you like to proceed with your application today, po?",
        "Batay po sa lahat ng ating napag-usapan, gusto po ba ninyong ituloy ang inyong application ngayon?",
    ),
    "closing": (
        "Wonderful! Thank you so much for your time today, po. "
        "A licensed insurance advisor will contact you within 24 hours to assist with the next steps.",
        "Napakaganda po niyan! Maraming salamat po sa inyong oras ngayon. "
        "Makikipag-ugnayan po sa inyo ang aming licensed insurance advisor sa loob ng 24 na oras "
        "para tulungan kayo sa mga susunod na hakbang.",
    ),
}


# ---------------------------------------------------------------------------
# Philippines Insurance Bot
# ---------------------------------------------------------------------------

@dataclass
class PHLeadProfile:
    """Lead profile for a Philippine market customer."""
    name: str = ""
    age: Optional[int] = None
    has_family: bool = False
    num_children: int = 0
    is_ofw: bool = False
    coverage_interest: List[str] = field(default_factory=list)
    pre_existing_conditions: str = ""
    monthly_budget_php: Optional[float] = None
    chosen_plan: str = ""
    beneficiary_name: str = ""
    objections: List[str] = field(default_factory=list)


class PhilippinesInsuranceBot:
    """
    Life insurance and bancassurance voice bot for the Philippine market.

    Supports:
    - Full Taglish conversation (Filipino + English mixed)
    - po/opo respect markers throughout
    - Local insurance terminology (hulog, lapse, rider, benepisyaryo)
    - OFW-specific coverage discussion
    - Cultural sensitivity (family-first framing)
    - Accent normalization for common Filipino phonetic variants

    Usage:
        bot = PhilippinesInsuranceBot()
        response = bot.respond("Gusto ko pong mag-avail ng insurance para sa pamilya ko")
    """

    def __init__(self, use_taglish: bool = True) -> None:
        self.use_taglish = use_taglish
        self.engine = LocalizationEngine()
        self.state = PHBotState.GREETING
        self.lead = PHLeadProfile()
        self.history: List[Dict[str, str]] = []
        self._turn = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def respond(self, customer_input: str) -> str:
        """Process customer input and return an appropriate Taglish response."""
        self._turn += 1

        # Normalize phonetic variants first
        lang = self.engine.detect_language(customer_input)
        normalized_input, normalizations = self.engine.normalize_accents(customer_input, lang)

        # Detect objections
        input_lower = normalized_input.lower()
        if any(w in input_lower for w in ["mahal", "expensive", "afford", "can't", "di kaya"]):
            self.lead.objections.append("cost_concern")
            return self._script("objection_expensive")

        if any(w in input_lower for w in ["think", "pag-isipan", "later", "balikan", "pag-aralan"]):
            self.lead.objections.append("needs_time")
            return self._script("objection_think")

        if any(w in input_lower for w in ["pre-existing", "may sakit", "diabetes", "puso", "heart"]):
            return self._script("objection_pre_existing")

        # Escalation
        if any(w in input_lower for w in ["supervisor", "manager", "reklamo", "complaint"]):
            self.state = PHBotState.ESCALATION
            return (
                "Naiintindihan ko po. Ililipat ko po kayo sa aming senior advisor na makakatulong sa inyo. "
                "Sandali lang po, hintayin kayo."
                if self.use_taglish
                else "I understand. I'm transferring you to a senior advisor who can assist you."
            )

        # State machine routing
        return self._route_state(normalized_input)

    def get_opening(self) -> str:
        """Return the bot's opening greeting in Taglish."""
        return self._script("greeting")

    def explain_term(self, term: str) -> str:
        """
        Explain a specific insurance term in Taglish.
        Called when customer asks about a specific term.
        """
        term_lower = term.lower()
        explanations = {
            "premium": self._script("explain_premium"),
            "hulog": self._script("explain_premium"),
            "beneficiary": self._script("explain_beneficiary"),
            "benepisyaryo": self._script("explain_beneficiary"),
            "rider": self._script("explain_rider"),
            "lapse": self._script("explain_lapse"),
        }
        result = explanations.get(term_lower)
        if result:
            return result
        return (
            f"Patawad po, maaari po bang linawin ang inyong tanong tungkol sa '{term}'? "
            "Gusto ko pong masiguro na mabibigyan kayo ng tamang sagot."
            if self.use_taglish
            else f"I'm sorry, could you clarify your question about '{term}'? I want to give you the right answer."
        )

    def assess_code_switch_quality(self, text: str) -> str:
        """Score the code-switch quality of a given text and return a report."""
        lang = self.engine.detect_language(text)
        quality = self.engine.score_code_switch_quality(text, lang)
        return (
            f"Language: {lang.value} | "
            f"Quality: {quality.quality_label()} (score={quality.score:.2f}) | "
            f"Local Terms: {quality.local_terms_used} | "
            f"Respect Markers: {quality.respect_markers_detected} | "
            f"Note: {quality.notes}"
        )

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _script(self, key: str) -> str:
        """Return either the Taglish or English version of a script line."""
        if key not in TAGLISH_SCRIPTS:
            return f"[Script key '{key}' not found]"
        english, taglish = TAGLISH_SCRIPTS[key]
        return taglish if self.use_taglish else english

    def _route_state(self, text: str) -> str:
        """Route to the appropriate response based on current state."""
        text_lower = text.lower()

        if self.state == PHBotState.GREETING:
            self.state = PHBotState.NEEDS_ASSESSMENT
            return self._script("ask_name")

        if self.state == PHBotState.NEEDS_ASSESSMENT:
            # Extract name if given
            if not self.lead.name and len(text.split()) <= 4:
                self.lead.name = text.strip().title()
                return (
                    f"Kumusta po kayo, {self.lead.name}! "
                    + self._script("ask_age")
                    if self.use_taglish
                    else f"Hello, {self.lead.name}! " + self._script("ask_age")
                )

            # Extract age
            import re
            age_match = re.search(r"\b(\d{2})\b", text)
            if age_match and not self.lead.age:
                self.lead.age = int(age_match.group(1))
                self.state = PHBotState.PRODUCT_PRESENTATION
                return self._script("ask_family")

            if any(w in text_lower for w in ["insurance", "life", "health", "coverage", "policy"]):
                self.state = PHBotState.PRODUCT_PRESENTATION
                return self._script("ask_coverage")

            return self._script("ask_age")

        if self.state == PHBotState.PRODUCT_PRESENTATION:
            if any(w in text_lower for w in ["life", "buhay", "kamatayan", "death", "disability"]):
                self.lead.coverage_interest.append("life")
                self.state = PHBotState.PREMIUM_DISCUSSION
                return self._script("present_life") + "\n\n" + self._script("ask_proceed")

            if any(w in text_lower for w in ["health", "ospital", "medikal", "hospital", "medical"]):
                self.lead.coverage_interest.append("health")
                self.state = PHBotState.PREMIUM_DISCUSSION
                return (
                    "Ang aming Comprehensive Health Insurance po ay sumasaklaw sa inpatient hospitalization, "
                    "outpatient consultations, at emergency care. "
                    + self._script("explain_premium")
                    if self.use_taglish
                    else "Our Comprehensive Health Insurance covers inpatient, outpatient, and emergency care. "
                    + self._script("explain_premium")
                )

            if any(w in text_lower for w in ["ofw", "abroad", "ibang bansa", "overseas"]):
                self.lead.is_ofw = True
                return (
                    "Para po sa OFW, espesyal na programa ang mayroon kami na tinatawag na OFW Life Protect. "
                    "Binibigyan nito ng PHP 1,000,000 na coverage ang inyong pamilya kahit nasa ibang bansa po kayo. "
                    if self.use_taglish
                    else "For OFWs, we have a special program called OFW Life Protect providing PHP 1,000,000 coverage for your family."
                )

            return self._script("ask_coverage")

        if self.state == PHBotState.PREMIUM_DISCUSSION:
            if any(w in text_lower for w in ["yes", "oo", "sige", "tara", "proceed", "apply"]):
                self.state = PHBotState.APPLICATION
                return self._script("closing")
            return self._script("objection_think")

        if self.state == PHBotState.APPLICATION:
            return self._script("closing")

        # Default fallback
        return (
            "Patawad po, hindi ko po lubos na naintindihan ang inyong sinabi. "
            "Maaari po ba kayong ulitin? Nandito po ako para tulungan kayo."
            if self.use_taglish
            else "I'm sorry, I didn't fully understand. Could you repeat that? I'm here to help you."
        )

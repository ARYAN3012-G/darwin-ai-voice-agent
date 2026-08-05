"""
Q3 Multilingual — Localization Engine
=======================================
Provides core localization capabilities shared by all native-language bots:

  1. Language Detection  — Detect primary language and code-switching patterns
  2. Code-Switch Quality — Score quality of Taglish / Bahasa Indonesia mixing
  3. Accent Normalization — Map phonetic variants to canonical terms
  4. Term Translation Table — Domain-specific finance/insurance term mappings
  5. Respect Marker Injection — Handle po/opo (Filipino), Bapak/Ibu (Indonesian)

Design Philosophy:
  - Never lose meaning when switching languages
  - Use LOCAL terminology preferred by customers (not textbook translation)
  - Respect cultural context: tone, formality, and social norms
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Language Codes
# ---------------------------------------------------------------------------

class Language(str, Enum):
    ENGLISH = "en"
    FILIPINO = "fil"
    TAGLISH = "taglish"         # Filipino-English mix
    BAHASA_INDONESIA = "id"
    BAHASA_COLLOQUIAL = "id_coll"  # Colloquial Indonesian with loanwords


# ---------------------------------------------------------------------------
# Code-Switch Quality
# ---------------------------------------------------------------------------

@dataclass
class CodeSwitchQuality:
    """
    Measures the quality of code-switching in a multilingual utterance.

    Attributes:
        score (float): 0.0 (poor) to 1.0 (excellent)
        primary_language: Detected dominant language
        switch_count: Number of language switches detected
        local_terms_used: Finance/insurance terms in local language found
        respect_markers_detected: po/opo or Bapak/Ibu detected
        notes: Qualitative notes on the switching quality
    """
    score: float = 0.0
    primary_language: Language = Language.ENGLISH
    switch_count: int = 0
    local_terms_used: List[str] = field(default_factory=list)
    respect_markers_detected: List[str] = field(default_factory=list)
    accent_variants_normalized: List[Tuple[str, str]] = field(default_factory=list)
    notes: str = ""

    def quality_label(self) -> str:
        if self.score >= 0.85:
            return "EXCELLENT"
        elif self.score >= 0.70:
            return "GOOD"
        elif self.score >= 0.50:
            return "FAIR"
        else:
            return "POOR"


# ---------------------------------------------------------------------------
# Philippine Domain Lexicon
# ---------------------------------------------------------------------------

# Filipino local terms → English equivalents (for display/logging)
PH_INSURANCE_LEXICON: Dict[str, str] = {
    # Core insurance terms
    "premium": "premium payment",
    "hulog": "installment/premium payment",
    "policy": "insurance policy",
    "polisa": "insurance policy",
    "coverage": "insurance coverage",
    "saklaw": "coverage",
    "benepisyo": "benefits",
    "benepisyaryo": "beneficiary",
    "beneficiary": "beneficiary",
    "rider": "optional add-on benefit",
    "lapse": "policy lapse (non-payment)",
    "matured": "policy matured",
    "surrender": "policy surrender",
    "face amount": "sum assured",
    "sum insured": "sum assured",

    # Health/medical terms
    "ospital": "hospital",
    "doktor": "doctor",
    "gamot": "medicine/prescription",
    "operasyon": "surgical operation",
    "medikal": "medical",
    "check-up": "medical check-up",
    "confinement": "hospitalization",
    "confined": "hospitalized",

    # Common objections in Filipino
    "mahal": "expensive",
    "di kaya": "cannot afford",
    "wala akong pera": "I don't have money",
    "pag-isipan ko muna": "let me think about it",
    "balikan ko na lang": "I'll just call back",
    "pag-aralan ko": "let me study it",
}

# Filipino accent/phonetic variant mapping
PH_ACCENT_VARIANTS: Dict[str, str] = {
    "imburance": "insurance",
    "enshurans": "insurance",
    "polici": "policy",
    "policyya": "policy",
    "premyum": "premium",
    "prebium": "premium",
    "benefisyaryo": "beneficiary",
    "benefisyari": "beneficiary",
    "kliyente": "client",
    "ospital": "hospital",
    "medikal": "medical",
    "doktor": "doctor",
    "klaym": "claim",
    "eksklusion": "exclusion",
}

# Respect markers (Filipino)
PH_RESPECT_MARKERS = ["po", "opo", "ho", "oho", "sir", "ma'am", "maam"]

# Common Taglish opening phrases
PH_TAGLISH_PHRASES = {
    "pwede bang malaman": "may I know",
    "gusto ko sanang": "I would like to",
    "paano po ang": "how do I",
    "magkano po ang": "how much is the",
    "meron po ba": "do you have",
    "may tanong lang po ako": "I just have a question",
    "saan ko makukuha": "where can I get",
    "kailan po": "when",
    "hanggang kailan": "until when / how long",
}


# ---------------------------------------------------------------------------
# Indonesian Domain Lexicon
# ---------------------------------------------------------------------------

# Indonesian local terms → English equivalents
ID_FINANCE_LEXICON: Dict[str, str] = {
    # Loan terms
    "cicilan": "installment payment",
    "angsuran": "installment / monthly payment",
    "tenor": "loan term / duration",
    "dp": "down payment",
    "uang muka": "down payment",
    "denda": "penalty / late fee",
    "bunga": "interest rate",
    "pokok": "principal amount",
    "jatuh tempo": "due date / maturity",
    "pembiayaan": "financing / loan",
    "kredit": "credit / loan",
    "pinjaman": "loan",
    "agunan": "collateral",
    "jaminan": "guarantee / collateral",
    "pelunasan": "full repayment / settlement",
    "restrukturisasi": "loan restructuring",
    "cek fisik": "physical inspection / appraisal",

    # Business terms
    "omset": "revenue / turnover",
    "modal": "capital",
    "usaha": "business",
    "toko": "store / shop",
    "laporan keuangan": "financial report",
    "npwp": "taxpayer identification number (TIN)",
    "siup": "business trading license",
    "akta": "notarized deed",

    # Common colloquial objections
    "berat": "burden / heavy (expensive)",
    "kemahalan": "too expensive",
    "ribet": "complicated / troublesome",
    "lama banget": "takes too long",
    "gak sanggup": "can't afford / unable",
    "pikir-pikir dulu": "let me think about it",
    "nanti saja": "later / not now",
}

# Indonesian accent/phonetic variants (regional dialects)
ID_ACCENT_VARIANTS: Dict[str, str] = {
    # Javanese influence
    "kredit e": "kreditnya",
    "cicilan e": "cicilannya",
    "iku": "itu",
    "opo": "apa",
    # Sundanese influence
    "kumaha": "bagaimana",
    "naon": "apa",
    # Colloquial shortenings
    "gak": "tidak",
    "nggak": "tidak",
    "enggak": "tidak",
    "gimana": "bagaimana",
    "emang": "memang",
    "bisa aja": "bisa saja",
    "udah": "sudah",
    "belom": "belum",
    "kalo": "kalau",
    "dong": "(softener particle)",
    "sih": "(softener particle)",
    "nih": "ini",
    "tuh": "itu",
}

# Indonesian formality markers
ID_FORMALITY_MARKERS = {
    "formal": ["Bapak", "Ibu", "Saudara", "Anda", "Beliau"],
    "informal": ["Kamu", "Lo", "Gue", "Lu"],
}


# ---------------------------------------------------------------------------
# Localization Engine
# ---------------------------------------------------------------------------

class LocalizationEngine:
    """
    Core localization engine supporting Filipino (Taglish) and
    Bahasa Indonesia (formal + colloquial) for financial services voice bots.

    Provides:
      - Language detection from text
      - Code-switch quality scoring
      - Accent normalization (phonetic variants → canonical)
      - Local term recognition and mapping
      - Respect marker detection (po/opo, Bapak/Ibu)
    """

    def __init__(self) -> None:
        # Build detection vocabularies
        self._ph_vocab = set(PH_INSURANCE_LEXICON.keys()) | set(PH_RESPECT_MARKERS)
        self._id_vocab = set(ID_FINANCE_LEXICON.keys())
        self._ph_accent_map = {k.lower(): v for k, v in PH_ACCENT_VARIANTS.items()}
        self._id_accent_map = {k.lower(): v for k, v in ID_ACCENT_VARIANTS.items()}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_language(self, text: str) -> Language:
        """
        Detect the primary language of the input text.
        Returns Language enum value.
        """
        text_lower = text.lower()
        tokens = set(re.findall(r"\b[a-zA-Z]+\b", text_lower))

        ph_hits = sum(1 for t in tokens if t in self._ph_vocab)
        id_hits = sum(1 for t in tokens if t in self._id_vocab)

        # Check for Filipino respect markers
        ph_respect = sum(1 for marker in PH_RESPECT_MARKERS if marker in text_lower)
        # Check for Indonesian formality markers
        id_formal = sum(
            1 for marker in ID_FORMALITY_MARKERS["formal"] if marker in text
        )

        ph_score = ph_hits * 2 + ph_respect * 3
        id_score = id_hits * 2 + id_formal * 3

        if ph_score == 0 and id_score == 0:
            return Language.ENGLISH
        if ph_score > id_score:
            # Check if it's pure Filipino or Taglish (mixed with English)
            english_tokens = sum(1 for t in tokens if len(t) > 3 and t.isalpha()
                                 and t not in self._ph_vocab)
            return Language.TAGLISH if english_tokens > 2 else Language.FILIPINO
        else:
            colloquial_markers = sum(
                1 for v in ID_ACCENT_VARIANTS if v.split()[0] in text_lower
            )
            return Language.BAHASA_COLLOQUIAL if colloquial_markers > 2 else Language.BAHASA_INDONESIA

    def normalize_accents(self, text: str, language: Language) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Normalize accent/phonetic variants to canonical forms.
        Returns (normalized_text, [(original, normalized), ...]) for tracing.
        """
        normalizations: List[Tuple[str, str]] = []
        accent_map = (
            self._ph_accent_map
            if language in (Language.FILIPINO, Language.TAGLISH)
            else self._id_accent_map
        )

        for variant, canonical in accent_map.items():
            pattern = re.compile(r"\b" + re.escape(variant) + r"\b", re.IGNORECASE)
            if pattern.search(text):
                text = pattern.sub(canonical, text)
                normalizations.append((variant, canonical))

        return text, normalizations

    def score_code_switch_quality(
        self, text: str, language: Language
    ) -> CodeSwitchQuality:
        """
        Score the quality of code-switching in an agent response.

        Evaluation criteria:
        1. Local terms used correctly (+2 per term)
        2. Respect markers present (+3 per marker, cap at 6)
        3. Smooth transitions between languages (no abrupt mid-sentence breaks)
        4. Phonetic variant normalization quality
        """
        quality = CodeSwitchQuality(primary_language=language)

        text_lower = text.lower()
        tokens = re.findall(r"\b[a-zA-Z]+\b", text_lower)

        # Score local finance terms
        if language in (Language.FILIPINO, Language.TAGLISH):
            for term in PH_INSURANCE_LEXICON:
                if term in text_lower:
                    quality.local_terms_used.append(term)
            for marker in PH_RESPECT_MARKERS:
                if marker in text_lower:
                    quality.respect_markers_detected.append(marker)
            # Count switches (alternation between PH and EN tokens)
            ph_positions = [i for i, t in enumerate(tokens) if t in self._ph_vocab]
            quality.switch_count = len(ph_positions)

        elif language in (Language.BAHASA_INDONESIA, Language.BAHASA_COLLOQUIAL):
            for term in ID_FINANCE_LEXICON:
                if term in text_lower:
                    quality.local_terms_used.append(term)
            for marker in ID_FORMALITY_MARKERS["formal"]:
                if marker in text:
                    quality.respect_markers_detected.append(marker)
            id_positions = [i for i, t in enumerate(tokens) if t in self._id_vocab]
            quality.switch_count = len(id_positions)

        # Compute composite score
        term_score = min(len(quality.local_terms_used) * 0.15, 0.45)
        marker_score = min(len(quality.respect_markers_detected) * 0.15, 0.30)
        switch_density = min(quality.switch_count / max(len(tokens), 1), 0.30)

        # Penalize if no local terms at all
        if not quality.local_terms_used:
            quality.score = 0.20
            quality.notes = "No local financial terms detected. Response appears fully English."
        else:
            quality.score = min(term_score + marker_score + switch_density + 0.25, 1.0)
            quality.notes = (
                f"Detected {len(quality.local_terms_used)} local term(s) and "
                f"{len(quality.respect_markers_detected)} respect marker(s)."
            )

        return quality

    def translate_term(self, term: str, language: Language) -> str:
        """
        Return the local-language equivalent of a financial term.
        Falls back to English if no translation exists.
        """
        term_lower = term.lower()
        if language in (Language.FILIPINO, Language.TAGLISH):
            # Return Filipino term if English is given
            for local, eng in PH_INSURANCE_LEXICON.items():
                if term_lower in eng.lower():
                    return local
        elif language in (Language.BAHASA_INDONESIA, Language.BAHASA_COLLOQUIAL):
            for local, eng in ID_FINANCE_LEXICON.items():
                if term_lower in eng.lower():
                    return local
        return term

    def explain_non_literal(self, phrase: str, language: Language) -> str:
        """
        Provide non-literal (idiomatic) explanations of local expressions.
        These are phrases that cannot be directly translated word-for-word.
        """
        _PH_NON_LITERAL: Dict[str, str] = {
            "hulog": (
                "'Hulog' literally means 'to drop/fall' but in insurance context means "
                "your premium installment payment — the amount you regularly pay to keep your policy active."
            ),
            "lapse": (
                "A 'lapse' means your policy has gone inactive because a premium payment was missed. "
                "In Filipino context, 'na-lapse ang policy mo' means your coverage has stopped temporarily."
            ),
            "rider": (
                "A 'rider' is not a person riding something — in insurance, it's an optional "
                "add-on benefit you attach to your main policy, like a critical illness or maternity rider."
            ),
            "pag-aralan ko": (
                "'Pag-aralan ko' literally means 'I will study it' but is a polite Filipino way "
                "of saying 'I need time to think about it.' The agent should acknowledge this respectfully."
            ),
        }

        _ID_NON_LITERAL: Dict[str, str] = {
            "tenor": (
                "'Tenor' in Indonesian banking means the loan duration/term — "
                "e.g., 'tenor 36 bulan' means a 36-month loan period. "
                "It comes from the Italian musical term but is now standard in Indonesian finance."
            ),
            "jatuh tempo": (
                "'Jatuh tempo' literally means 'falls due' — it refers to the loan due date or maturity. "
                "When someone says 'sudah jatuh tempo', it means the payment is now overdue."
            ),
            "dp": (
                "'DP' is a loanword abbreviation for 'Down Payment' and is universally understood "
                "in Indonesian retail/property context. A larger DP means smaller monthly cicilan."
            ),
            "ribet": (
                "'Ribet' is colloquial for 'rumit' (complicated) — when a customer says "
                "'prosesnya ribet', they mean the application process feels overly complicated or burdensome."
            ),
        }

        phrase_lower = phrase.lower()
        if language in (Language.FILIPINO, Language.TAGLISH):
            return _PH_NON_LITERAL.get(phrase_lower, f"No non-literal explanation available for '{phrase}'.")
        elif language in (Language.BAHASA_INDONESIA, Language.BAHASA_COLLOQUIAL):
            return _ID_NON_LITERAL.get(phrase_lower, f"No non-literal explanation available for '{phrase}'.")
        return f"Language not recognized for '{phrase}'."

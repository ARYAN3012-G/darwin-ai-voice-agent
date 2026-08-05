"""
Q3 Multilingual — Test Suite
==============================
Tests both the Philippines Insurance Bot and Indonesia Loan Bot with
realistic multilingual dialogues. Evaluates:

  1. Code-switch quality scoring for agent responses
  2. Accent/phonetic variant normalization
  3. Local term recognition and usage
  4. Respect marker injection (po/opo, Bapak/Ibu)
  5. Non-literal translation explanations
  6. Objection handling in native language
"""

from __future__ import annotations

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from q3_multilingual.philippines_bot import PhilippinesInsuranceBot
from q3_multilingual.indonesia_bot import IndonesiaLoanBot
from q3_multilingual.localization_engine import LocalizationEngine, Language


# ---------------------------------------------------------------------------
# Philippines Test Dialogues
# ---------------------------------------------------------------------------

PH_DIALOGUE_1 = [
    "Gusto ko pong malaman ang tungkol sa inyong life insurance.",
    "Maria Santos po.",
    "Tatlumpu't lima po.",
    "Oo po, may asawa at dalawang anak po ako.",
    "Life insurance po, para protektado ang pamilya ko.",
    "Magkano po ang buwanang hulog?",
    "Mahal naman po. Hindi ko po kaya ang PHP 1,200 bawat buwan.",
    "Sige po, pag-isipan ko muna.",
]

PH_DIALOGUE_2_OFW = [
    "Hello po, OFW po ako sa Saudi Arabia, gusto ko pong mag-avail ng insurance para sa pamilya ko.",
    "Hindi pa po ako sigurado kung life o health insurance ang kukunin ko.",
    "May pre-existing condition po ako, may diabetes.",
    "Magkano po ang rider para sa critical illness?",
    "Yes po, gusto ko pong mag-proceed.",
]

PH_ACCENT_TESTS = [
    ("Gusto ko pong malaman ang enshurans na may kliyente ako.", "Insurance with client inquiry"),
    ("Magkano po ang premyum ng polici?", "Premium + policy accent test"),
    ("Pwede bang magfile ng klaym online?", "Claim filing query"),
]

# ---------------------------------------------------------------------------
# Indonesia Test Dialogues
# ---------------------------------------------------------------------------

ID_DIALOGUE_FORMAL = [
    "Selamat pagi, saya ingin menanyakan tentang pinjaman untuk usaha saya.",
    "Saya Budi Santoso.",
    "Usaha saya sudah berjalan 3 tahun, toko kelontong.",
    "Omset sekitar 50 juta per bulan.",
    "Saya butuh pinjaman sekitar 200 juta.",
    "36 bulan untuk tenornya.",
    "Saya punya sertifikat tanah untuk agunan.",
    "Apa saja dokumen yang diperlukan?",
    "Oke, saya siap lanjutkan prosesnya.",
]

ID_DIALOGUE_COLLOQUIAL = [
    "Halo, mau nanya soal kredit usaha dong.",
    "Budi.",
    "Udah 2 tahun lebih nih usahanya.",
    "Omsetnya sekitar 30-40 juta per bulan.",
    "Butuh modal sekitar 150 juta.",
    "Proses pengajuannya ribet gak sih?",
    "Kira-kira bunganya berapa persen per tahun?",
    "Gimana kalau telat bayar cicilan?",
    "Oke deh, lanjut aja ke pengajuan.",
]

ID_ACCENT_TESTS = [
    ("Iku piye cicilannya?", "Javanese accent (iku=itu, piye=bagaimana)"),
    ("Kumaha caranya ngajuin kredit?", "Sundanese accent (kumaha=bagaimana)"),
    ("Gue mau nanya soal DP-nya dong.", "Betawi/Jakarta colloquial"),
]


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

def separator(title: str = "", width: int = 65) -> None:
    if title:
        print(f"\n{'─'*width}")
        print(f"  {title}")
        print(f"{'─'*width}")
    else:
        print("─" * width)


def run_ph_test(dialogue: list[str], title: str, bot_kwargs: dict = None) -> None:
    """Run a Philippines bot dialogue test."""
    separator(title)
    bot = PhilippinesInsuranceBot(**(bot_kwargs or {}))
    print(f"\n  [AGENT OPENING]\n  {bot.get_opening()}\n")

    for i, utterance in enumerate(dialogue, 1):
        print(f"  [{i}] CUSTOMER : {utterance}")
        response = bot.respond(utterance)
        print(f"      AGENT    : {response}")

        # Score the response quality
        quality_report = bot.assess_code_switch_quality(response)
        print(f"      QUALITY  : {quality_report}\n")


def run_ph_accent_tests() -> None:
    """Test Philippine accent normalization."""
    separator("PH ACCENT NORMALIZATION TESTS")
    engine = LocalizationEngine()
    for text, description in PH_ACCENT_TESTS:
        lang = engine.detect_language(text)
        normalized, changes = engine.normalize_accents(text, lang)
        print(f"\n  Test    : {description}")
        print(f"  Input   : {text}")
        print(f"  Language: {lang.value}")
        if changes:
            for orig, norm in changes:
                print(f"  Norm    : '{orig}' → '{norm}'")
        else:
            print(f"  Norm    : (no accent variants detected)")
        print(f"  Output  : {normalized}")


def run_ph_non_literal_tests() -> None:
    """Test non-literal term explanations."""
    separator("PH NON-LITERAL TERM EXPLANATIONS")
    engine = LocalizationEngine()
    for term in ["hulog", "lapse", "rider", "pag-aralan ko"]:
        explanation = engine.explain_non_literal(term, Language.TAGLISH)
        print(f"\n  Term       : '{term}'")
        print(f"  Explanation: {explanation}")


def run_id_test(dialogue: list[str], title: str, use_formal: bool = True) -> None:
    """Run an Indonesia bot dialogue test."""
    separator(title)
    bot = IndonesiaLoanBot(use_formal=use_formal)
    print(f"\n  [AGENT OPENING]\n  {bot.get_opening()}\n")

    for i, utterance in enumerate(dialogue, 1):
        print(f"  [{i}] CUSTOMER : {utterance}")
        response = bot.respond(utterance)
        print(f"      AGENT    : {response}")

        quality_report = bot.assess_code_switch_quality(response)
        print(f"      QUALITY  : {quality_report}\n")


def run_id_accent_tests() -> None:
    """Test Indonesian accent normalization."""
    separator("ID ACCENT NORMALIZATION TESTS (Regional Dialects)")
    engine = LocalizationEngine()
    for text, description in ID_ACCENT_TESTS:
        lang = engine.detect_language(text)
        normalized, changes = engine.normalize_accents(text, lang)
        print(f"\n  Test    : {description}")
        print(f"  Input   : {text}")
        print(f"  Language: {lang.value}")
        if changes:
            for orig, norm in changes:
                print(f"  Norm    : '{orig}' → '{norm}'")
        print(f"  Output  : {normalized}")


def run_id_non_literal_tests() -> None:
    """Test Indonesian non-literal explanations."""
    separator("ID NON-LITERAL TERM EXPLANATIONS")
    engine = LocalizationEngine()
    for term in ["tenor", "jatuh tempo", "dp", "ribet"]:
        explanation = engine.explain_non_literal(term, Language.BAHASA_INDONESIA)
        print(f"\n  Term       : '{term}'")
        print(f"  Explanation: {explanation}")


def run_id_loan_simulation() -> None:
    """Demonstrate the loan simulation calculator."""
    separator("ID LOAN SIMULATION DEMO")
    bot = IndonesiaLoanBot(use_formal=True)
    scenarios = [
        (100_000_000, 15.0, 24, "Rp 100M, 15% p.a., 24 months"),
        (200_000_000, 12.0, 36, "Rp 200M, 12% p.a., 36 months"),
        (500_000_000, 14.0, 60, "Rp 500M, 14% p.a., 60 months"),
    ]
    for principal, rate, tenor, label in scenarios:
        print(f"\n  Scenario: {label}")
        sim = bot.simulate_loan(principal, rate, tenor)
        print(sim)


def main() -> None:
    print("\n" + "═" * 65)
    print("  Q3 MULTILINGUAL BOTS — TEST SUITE")
    print("  Philippines (Taglish) + Indonesia (Bahasa Indonesia)")
    print("═" * 65)

    # ── Philippines Tests ──
    print("\n" + "█" * 65)
    print("  🇵🇭  PHILIPPINES INSURANCE BOT TESTS")
    print("█" * 65)

    run_ph_test(
        PH_DIALOGUE_1,
        "PH TEST 1 — Life Insurance (Taglish, Complete Qualification)"
    )
    run_ph_test(
        PH_DIALOGUE_2_OFW,
        "PH TEST 2 — OFW Customer + Pre-existing Condition",
        {"use_taglish": True}
    )
    run_ph_accent_tests()
    run_ph_non_literal_tests()

    # ── Indonesia Tests ──
    print("\n" + "█" * 65)
    print("  🇮🇩  INDONESIA LOAN BOT TESTS")
    print("█" * 65)

    run_id_test(
        ID_DIALOGUE_FORMAL,
        "ID TEST 1 — Business Loan (Formal Bahasa Indonesia)",
        use_formal=True
    )
    run_id_test(
        ID_DIALOGUE_COLLOQUIAL,
        "ID TEST 2 — Consumer Loan (Colloquial/Informal Bahasa)",
        use_formal=False
    )
    run_id_accent_tests()
    run_id_non_literal_tests()
    run_id_loan_simulation()

    print("\n" + "═" * 65)
    print("  ALL MULTILINGUAL TESTS COMPLETED")
    print("═" * 65 + "\n")


if __name__ == "__main__":
    main()

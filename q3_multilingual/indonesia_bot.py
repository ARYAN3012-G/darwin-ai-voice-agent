"""
Q3 Multilingual — Indonesia Loan Bot (Bahasa Indonesia)
=========================================================
A consumer finance and personal/business loan bot for the Indonesian market.

Language Profile:
- Formal Bahasa Indonesia (for SME/business contexts)
- Colloquial Bahasa (for retail consumer loan customers)
- Handles regional accent variations: Javanese (Central/East Java),
  Sundanese (West Java), Betawi (Jakarta)
- Common loanwords from English integrated naturally into responses

Local Finance Terms Used:
  cicilan / angsuran — installment payment
  tenor — loan term duration
  denda — penalty / late fee
  DP (uang muka) — down payment
  jatuh tempo — due date / loan maturity
  pembiayaan — financing
  agunan / jaminan — collateral / guarantee
  bunga — interest rate
  pelunasan — full loan settlement
  omset — business revenue/turnover
  NPWP — Taxpayer ID
  SIUP — Business trading license

Cultural Context:
- Indonesians prefer Bapak/Ibu as respectful address forms
- Colloquial Indonesian uses gak/nggak for "tidak" (no/not)
- "Ribet" is very commonly used for "complicated"
- Customers may ask about "restrukturisasi" (loan restructuring) if facing difficulty
- Formal tone for new applicants; warm/colloquial for existing customers
"""

from __future__ import annotations

import re
import sys
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from q3_multilingual.localization_engine import (
    Language,
    LocalizationEngine,
    ID_FINANCE_LEXICON,
    ID_FORMALITY_MARKERS,
)


# ---------------------------------------------------------------------------
# Bot State
# ---------------------------------------------------------------------------

class IDBotState(str, Enum):
    GREETING = "greeting"
    IDENTIFICATION = "identification"
    NEEDS_ASSESSMENT = "needs_assessment"
    PRODUCT_PRESENTATION = "product_presentation"
    ELIGIBILITY_CHECK = "eligibility_check"
    DOCUMENT_EXPLANATION = "document_explanation"
    OBJECTION = "objection"
    APPLICATION = "application"
    ESCALATION = "escalation"
    CLOSING = "closing"


# ---------------------------------------------------------------------------
# Indonesian Script Library
# ---------------------------------------------------------------------------

# Entries: (Formal Bahasa, Colloquial Bahasa)
ID_SCRIPTS: Dict[str, Tuple[str, str]] = {
    "greeting_formal": (
        "Selamat pagi/siang, terima kasih telah menghubungi layanan kami. "
        "Saya siap membantu Bapak/Ibu untuk informasi pinjaman atau pembiayaan usaha. "
        "Ada yang bisa saya bantu?",
        "Halo! Makasih udah hubungin kami. "
        "Bisa saya bantu soal pinjaman atau kredit yang Bapak/Ibu butuhkan?",
    ),
    "ask_name": (
        "Boleh saya ketahui nama Bapak/Ibu terlebih dahulu?",
        "Boleh tau nama Bapak/Ibu dulu?",
    ),
    "ask_loan_type": (
        "Apakah Bapak/Ibu membutuhkan pinjaman untuk keperluan pribadi atau untuk modal usaha?",
        "Bapak/Ibu butuh pinjaman buat pribadi atau buat usaha?",
    ),
    "ask_loan_amount": (
        "Berapa jumlah pembiayaan yang Bapak/Ibu butuhkan?",
        "Bapak/Ibu butuh pinjaman berapa?",
    ),
    "ask_tenor": (
        "Untuk tenor berapa lama? Kami menyediakan pilihan 12, 24, 36, hingga 60 bulan.",
        "Mau tenor berapa bulan? Kami ada pilihan 12, 24, 36, sampai 60 bulan.",
    ),
    "ask_business_duration": (
        "Sudah berapa lama usaha Bapak/Ibu berjalan?",
        "Udah berapa lama usahanya jalan?",
    ),
    "ask_monthly_revenue": (
        "Berapa rata-rata omset atau penghasilan bulanan usaha Bapak/Ibu?",
        "Omset per bulannya kira-kira berapa?",
    ),
    "ask_collateral": (
        "Apakah Bapak/Ibu memiliki aset yang dapat dijadikan agunan, seperti sertifikat tanah atau BPKB kendaraan?",
        "Punya jaminan gak? Misalnya sertifikat tanah atau BPKB kendaraan?",
    ),
    "explain_cicilan": (
        "Cicilan atau angsuran bulanan Bapak/Ibu akan ditentukan berdasarkan pokok pinjaman, "
        "suku bunga, dan tenor yang dipilih. Cicilan dihitung dengan metode anuitas menurun.",
        "Jadi, cicilan per bulannya itu tergantung dari pinjaman, bunga, sama tenor yang dipilih. "
        "Makin panjang tenornya, makin kecil cicilannya, tapi total bunganya lebih besar.",
    ),
    "explain_tenor": (
        "Tenor adalah jangka waktu pinjaman Bapak/Ibu. "
        "Semakin panjang tenor, semakin kecil cicilan bulanannya, "
        "namun total bunga yang dibayarkan akan lebih besar.",
        "Tenor itu durasi pinjamannya. Makin panjang tenornya, cicilan lebih kecil, "
        "tapi bunganya lebih banyak. Kalau mau hemat bunga, pilih tenor yang lebih pendek.",
    ),
    "explain_denda": (
        "Apabila pembayaran cicilan terlambat, akan dikenakan denda sebesar 0,1% per hari "
        "dari jumlah cicilan yang tertunggak. Kami sarankan agar pembayaran selalu dilakukan tepat waktu.",
        "Kalau telat bayar cicilan, ada denda 0,1% per hari dari cicilan yang nunggak. "
        "Sebaiknya bayar tepat waktu ya Bapak/Ibu, biar gak kena denda.",
    ),
    "explain_jatuh_tempo": (
        "Jatuh tempo adalah tanggal jatuh tempo pembayaran angsuran Bapak/Ibu setiap bulannya. "
        "Kami akan mengirimkan notifikasi pengingat 3 hari sebelum jatuh tempo.",
        "Jatuh tempo itu tanggal bayar cicilan tiap bulannya. "
        "Kami akan kasih reminder 3 hari sebelumnya lewat SMS atau WA.",
    ),
    "explain_dp": (
        "Uang muka atau DP adalah pembayaran awal yang dibayarkan di muka sebelum pinjaman diproses. "
        "Semakin besar DP, semakin kecil cicilan dan total bunga yang dibayarkan.",
        "DP itu pembayaran pertama di awal sebelum kredit berjalan. "
        "Makin gede DP-nya, makin kecil cicilannya nanti.",
    ),
    "explain_documents": (
        "Dokumen yang diperlukan untuk pengajuan pinjaman usaha antara lain: "
        "KTP, NPWP, rekening koran 6 bulan terakhir, laporan keuangan 2 tahun, "
        "SIUP/NIB, dan dokumen agunan (jika ada).",
        "Dokumennya yang dibutuhkan: KTP, NPWP, mutasi rekening 6 bulan, "
        "laporan keuangan 2 tahun, SIUP atau NIB, sama dokumen jaminan kalau ada.",
    ),
    "objection_expensive": (
        "Saya memahami kekhawatiran Bapak/Ibu mengenai cicilan. "
        "Kami dapat menyesuaikan tenor dan jumlah pinjaman agar cicilan lebih ringan dan sesuai kemampuan. "
        "Boleh saya bantu hitung simulasinya?",
        "Saya ngerti Bapak/Ibu merasa berat. "
        "Tenang, kita bisa sesuaikan tenor dan jumlah pinjaman supaya cicilannya gak terlalu berat. "
        "Mau saya bantu hitung dulu?",
    ),
    "objection_complicated": (
        "Saya memahami bahwa proses pengajuan terasa rumit. "
        "Jangan khawatir, tim kami akan memandu Bapak/Ibu langkah demi langkah. "
        "Saya juga dapat membantu menyiapkan checklist dokumen untuk mempermudah prosesnya.",
        "Saya tau prosesnya keliatan ribet. "
        "Santai aja, kami bakal bantu step by step. "
        "Nanti saya kirimkan checklist dokumennya juga supaya lebih gampang.",
    ),
    "objection_slow": (
        "Proses persetujuan kami adalah 10–15 hari kerja setelah dokumen lengkap diterima. "
        "Jika Bapak/Ibu memiliki keperluan yang mendesak, kami juga memiliki produk Kredit Cepat "
        "yang dapat disetujui dalam 3 hari kerja untuk pinjaman hingga Rp 200 juta.",
        "Proses persetujuannya 10–15 hari kerja setelah dokumen lengkap. "
        "Tapi kalau urgent, kami ada produk Kredit Cepat yang bisa cair dalam 3 hari "
        "untuk pinjaman sampai Rp 200 juta.",
    ),
    "ask_proceed": (
        "Berdasarkan informasi yang sudah Bapak/Ibu berikan, apakah Bapak/Ibu siap untuk melanjutkan proses pengajuan?",
        "Dari info yang udah dikasih, Bapak/Ibu udah siap lanjut ke proses pengajuannya?",
    ),
    "closing": (
        "Terima kasih banyak atas kepercayaan Bapak/Ibu. "
        "Tim kami akan menghubungi Bapak/Ibu dalam 1x24 jam untuk konfirmasi dokumen dan langkah selanjutnya. "
        "Semoga sukses usahanya!",
        "Makasih banyak ya Bapak/Ibu! "
        "Tim kami bakal hubungi dalam 1x24 jam untuk konfirmasi dokumen. "
        "Semoga lancar dan sukses usahanya!",
    ),
}


# ---------------------------------------------------------------------------
# Indonesia Loan Bot
# ---------------------------------------------------------------------------

@dataclass
class IDLeadProfile:
    """Lead profile for Indonesian market customer."""
    name: str = ""
    formality: str = "formal"  # "formal" or "informal"
    loan_type: str = ""        # "personal" or "business"
    business_name: str = ""
    operating_months: Optional[int] = None
    monthly_revenue_idr: Optional[float] = None
    loan_amount_idr: Optional[float] = None
    preferred_tenor_months: Optional[int] = None
    has_collateral: Optional[bool] = None
    objections: List[str] = field(default_factory=list)
    region_accent: str = ""    # e.g. "javanese", "sundanese", "betawi"


class IndonesiaLoanBot:
    """
    Consumer finance and business loan bot for the Indonesian market.

    Supports:
    - Formal Bahasa Indonesia (Bapak/Ibu) for business loan contexts
    - Colloquial Bahasa (gak, gimana, ribet, cicilan, tenor)
    - Regional accent normalization (Javanese, Sundanese, Betawi)
    - Local financial terms (cicilan, tenor, denda, DP, jatuh tempo)
    - Loan simulation based on collected parameters

    Usage:
        bot = IndonesiaLoanBot(use_formal=True)
        response = bot.respond("Saya mau pinjam modal untuk usaha saya")
    """

    def __init__(self, use_formal: bool = True) -> None:
        self.use_formal = use_formal
        self.engine = LocalizationEngine()
        self.state = IDBotState.GREETING
        self.lead = IDLeadProfile()
        self.history: List[Dict[str, str]] = []
        self._turn = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_opening(self) -> str:
        """Return opening greeting in appropriate formality level."""
        return self._script("greeting_formal")

    def respond(self, customer_input: str) -> str:
        """Process customer input and return appropriate Indonesian response."""
        self._turn += 1

        # Normalize accent/dialect variants
        lang = Language.BAHASA_INDONESIA if self.use_formal else Language.BAHASA_COLLOQUIAL
        normalized, normalizations = self.engine.normalize_accents(customer_input, lang)

        # Adjust formality if colloquial markers detected
        if any(marker in normalized.lower() for marker in ["gak", "nggak", "gimana", "ribet", "udah", "kalo"]):
            self.use_formal = False
            self.lead.formality = "informal"
            lang = Language.BAHASA_COLLOQUIAL

        input_lower = normalized.lower()

        # Detect objections
        if any(w in input_lower for w in ["mahal", "berat", "kemahalan", "gak sanggup"]):
            self.lead.objections.append("cost")
            return self._script("objection_expensive")

        if any(w in input_lower for w in ["ribet", "rumit", "susah", "complicated"]):
            self.lead.objections.append("complexity")
            return self._script("objection_complicated")

        if any(w in input_lower for w in ["lama", "lambat", "lama banget", "kapan"]):
            self.lead.objections.append("speed")
            return self._script("objection_slow")

        # Escalation
        if any(w in input_lower for w in ["manajer", "atasan", "komplain", "supervisor", "keluhan"]):
            self.state = IDBotState.ESCALATION
            return (
                "Baik Bapak/Ibu, saya akan segera menghubungkan dengan supervisor kami. "
                "Mohon tunggu sebentar."
                if self.use_formal
                else "Oke, saya sambungkan ke supervisor ya. Tunggu bentar."
            )

        # Term explanation requests
        for term in ["cicilan", "tenor", "denda", "dp", "uang muka", "jatuh tempo", "agunan", "jaminan"]:
            if term in input_lower:
                return self._explain_term(term)

        return self._route_state(normalized)

    def simulate_loan(
        self,
        principal_idr: float,
        annual_rate_pct: float,
        tenor_months: int,
    ) -> str:
        """
        Calculate and return a loan simulation in Indonesian.
        Uses declining balance method.
        """
        monthly_rate = annual_rate_pct / 100 / 12
        if monthly_rate == 0:
            monthly_payment = principal_idr / tenor_months
        else:
            monthly_payment = (
                principal_idr * monthly_rate * (1 + monthly_rate) ** tenor_months
            ) / ((1 + monthly_rate) ** tenor_months - 1)

        total_payment = monthly_payment * tenor_months
        total_interest = total_payment - principal_idr

        def fmt(n: float) -> str:
            return f"Rp {n:,.0f}".replace(",", ".")

        return (
            f"Simulasi Kredit:\n"
            f"  Pokok Pinjaman  : {fmt(principal_idr)}\n"
            f"  Suku Bunga      : {annual_rate_pct:.1f}% per tahun\n"
            f"  Tenor           : {tenor_months} bulan\n"
            f"  Cicilan/Bulan   : {fmt(monthly_payment)}\n"
            f"  Total Pembayaran: {fmt(total_payment)}\n"
            f"  Total Bunga     : {fmt(total_interest)}"
        )

    def assess_code_switch_quality(self, text: str) -> str:
        """Score the code-switch quality of Indonesian text."""
        lang = self.engine.detect_language(text)
        quality = self.engine.score_code_switch_quality(text, lang)
        return (
            f"Language: {lang.value} | "
            f"Quality: {quality.quality_label()} (score={quality.score:.2f}) | "
            f"Local Terms: {quality.local_terms_used} | "
            f"Formality Markers: {quality.respect_markers_detected} | "
            f"Note: {quality.notes}"
        )

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _script(self, key: str) -> str:
        """Return formal or colloquial script version."""
        if key not in ID_SCRIPTS:
            return f"[Script key '{key}' not found]"
        formal, colloquial = ID_SCRIPTS[key]
        return formal if self.use_formal else colloquial

    def _explain_term(self, term: str) -> str:
        """Return explanation for a specific financial term."""
        term_scripts = {
            "cicilan": "explain_cicilan",
            "angsuran": "explain_cicilan",
            "tenor": "explain_tenor",
            "denda": "explain_denda",
            "dp": "explain_dp",
            "uang muka": "explain_dp",
            "jatuh tempo": "explain_jatuh_tempo",
            "agunan": (
                "Agunan adalah aset yang Bapak/Ibu berikan sebagai jaminan pinjaman. "
                "Jika pinjaman tidak dilunasi, bank berhak mencairkan agunan tersebut."
                if self.use_formal
                else "Agunan itu jaminan yang Bapak/Ibu kasih ke bank. "
                "Kalau pinjaman gak dilunasi, bank bisa eksekusi agunannya."
            ),
            "jaminan": (
                "Agunan adalah aset yang Bapak/Ibu berikan sebagai jaminan pinjaman. "
                "Jika pinjaman tidak dilunasi, bank berhak mencairkan agunan tersebut."
                if self.use_formal
                else "Jaminan itu aset buat backing pinjaman. "
                "Kalau macet, bank eksekusi jaminannya."
            ),
        }
        script_key = term_scripts.get(term.lower())
        if isinstance(script_key, str) and script_key in ID_SCRIPTS:
            return self._script(script_key)
        elif isinstance(script_key, str) and "Agunan" in script_key:
            return script_key
        return (
            f"Mohon maaf, saya belum memiliki penjelasan untuk istilah '{term}'. "
            "Apakah ada pertanyaan lain yang bisa saya bantu?"
            if self.use_formal
            else f"Maaf, belum ada penjelasan untuk '{term}'. Ada pertanyaan lain?"
        )

    def _route_state(self, text: str) -> str:
        """Route to appropriate response based on conversation state."""
        text_lower = text.lower()

        if self.state == IDBotState.GREETING:
            self.state = IDBotState.IDENTIFICATION
            return self._script("ask_name")

        if self.state == IDBotState.IDENTIFICATION:
            if not self.lead.name and len(text.split()) <= 5:
                self.lead.name = text.strip().title()
            self.state = IDBotState.NEEDS_ASSESSMENT
            return self._script("ask_loan_type")

        if self.state == IDBotState.NEEDS_ASSESSMENT:
            if any(w in text_lower for w in ["usaha", "bisnis", "toko", "modal", "business"]):
                self.lead.loan_type = "business"
                self.state = IDBotState.ELIGIBILITY_CHECK
                return self._script("ask_business_duration")
            elif any(w in text_lower for w in ["pribadi", "personal", "konsumtif", "rumah tangga"]):
                self.lead.loan_type = "personal"
                self.state = IDBotState.PRODUCT_PRESENTATION
                return self._script("ask_loan_amount")
            return self._script("ask_loan_type")

        if self.state == IDBotState.ELIGIBILITY_CHECK:
            months_match = re.search(r"(\d+)\s*(?:bulan|month)", text_lower)
            years_match = re.search(r"(\d+)\s*(?:tahun|year)", text_lower)
            if months_match:
                self.lead.operating_months = int(months_match.group(1))
            elif years_match:
                self.lead.operating_months = int(years_match.group(1)) * 12

            if self.lead.operating_months and self.lead.operating_months < 12:
                return (
                    "Mohon maaf Bapak/Ibu, untuk pinjaman usaha kami memerlukan minimal 12 bulan operasional. "
                    "Saat ini usaha Bapak/Ibu belum memenuhi kriteria tersebut. "
                    "Apakah ada produk lain yang bisa saya bantu informasikan?"
                    if self.use_formal
                    else "Maaf, untuk pinjaman usaha minimal udah 12 bulan jalan dulu ya. "
                    "Usaha Bapak/Ibu belum memenuhi kriteria. Ada produk lain yang mau ditanyain?"
                )

            self.state = IDBotState.PRODUCT_PRESENTATION
            return self._script("ask_monthly_revenue")

        if self.state == IDBotState.PRODUCT_PRESENTATION:
            amount_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:juta|ribu|rb|m|million)?", text_lower)
            if amount_match:
                num = float(amount_match.group(1).replace(",", "").replace(".", ""))
                if "juta" in text_lower or "m" in text_lower:
                    num *= 1_000_000
                elif "ribu" in text_lower or "rb" in text_lower:
                    num *= 1_000
                if not self.lead.monthly_revenue_idr:
                    self.lead.monthly_revenue_idr = num
                    return self._script("ask_loan_amount")
                elif not self.lead.loan_amount_idr:
                    self.lead.loan_amount_idr = num
                    self.state = IDBotState.DOCUMENT_EXPLANATION
                    return self._script("ask_tenor")

            self.state = IDBotState.DOCUMENT_EXPLANATION
            return self._script("ask_collateral")

        if self.state == IDBotState.DOCUMENT_EXPLANATION:
            # Provide document checklist
            if any(w in text_lower for w in ["dokumen", "berkas", "syarat", "persyaratan", "dokumen apa"]):
                return self._script("explain_documents")

            # Show simulation if we have enough data
            if self.lead.loan_amount_idr:
                sim = self.simulate_loan(self.lead.loan_amount_idr, 15.0, 36)
                self.state = IDBotState.APPLICATION
                return (
                    ("Berikut adalah simulasi pinjaman Bapak/Ibu:\n\n" + sim + "\n\n"
                     + self._script("ask_proceed"))
                    if self.use_formal
                    else ("Ini simulasi pinjamannya:\n\n" + sim + "\n\n" + self._script("ask_proceed"))
                )

            return self._script("explain_documents")

        if self.state == IDBotState.APPLICATION:
            if any(w in text_lower for w in ["ya", "iya", "setuju", "oke", "lanjut", "proses"]):
                self.state = IDBotState.CLOSING
                return self._script("closing")
            return self._script("objection_expensive")

        if self.state == IDBotState.CLOSING:
            return self._script("closing")

        return (
            "Mohon maaf, saya belum memahami pertanyaan Bapak/Ibu. "
            "Bisa diulang kembali? Saya siap membantu."
            if self.use_formal
            else "Maaf, saya kurang paham. Bisa diulangi? Saya siap bantu."
        )

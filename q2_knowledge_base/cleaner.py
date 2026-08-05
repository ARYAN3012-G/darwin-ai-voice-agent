"""
Q2 Knowledge Base — Document Cleaner
=====================================
Handles all ingestion-time document processing:
  1. Header / Footer stripping
  2. Whitespace normalization
  3. Heading & date standardization
  4. Near-duplicate detection via Jaccard similarity
  5. PII detection and masking (email, phone, TIN, SSN, credit card)

All operations are deterministic and logged for auditability.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .schema import PIIRecord, PIIType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PII Regex Patterns
# ---------------------------------------------------------------------------

_PII_PATTERNS: List[Tuple[PIIType, re.Pattern]] = [
    (
        PIIType.EMAIL,
        re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE),
    ),
    (
        PIIType.PHONE,
        re.compile(
            r"(\+?\d{1,3}[\s\-.]?)?"
            r"(\(?\d{2,4}\)?[\s\-.]?)?"
            r"\d{3,4}[\s\-.]?\d{4}",
            re.IGNORECASE,
        ),
    ),
    (
        PIIType.TIN,
        re.compile(r"\b\d{3}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{3}\b"),  # PH TIN format
    ),
    (
        PIIType.SSN,
        re.compile(r"\b\d{3}[\s\-]\d{2}[\s\-]\d{4}\b"),
    ),
    (
        PIIType.CREDIT_CARD,
        re.compile(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"),
    ),
]

# Headers/footers commonly found in scraped or exported documents
_HEADER_FOOTER_PATTERNS: List[re.Pattern] = [
    re.compile(r"^(page\s+\d+\s+of\s+\d+)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(confidential|internal use only|proprietary)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(copyright\s+©?\s*\d{4}.*)", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*-{3,}\s*$", re.MULTILINE),                 # horizontal rules
    re.compile(r"^\s*={3,}\s*$", re.MULTILINE),
    re.compile(r"^(table of contents|toc)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^(printed on|generated on|report date).*$", re.IGNORECASE | re.MULTILINE),
]

# Date normalization: convert various formats to ISO 8601 (YYYY-MM-DD)
_DATE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # DD/MM/YYYY or MM/DD/YYYY  (ambiguous — treat as MM/DD/YYYY)
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"), r"\3-\1-\2"),
    # DD-MM-YYYY
    (re.compile(r"\b(\d{1,2})-(\d{1,2})-(\d{4})\b"), r"\3-\1-\2"),
    # Month DD, YYYY (e.g. January 5, 2024)
    (
        re.compile(
            r"\b(January|February|March|April|May|June|July|August|"
            r"September|October|November|December)\s+(\d{1,2}),\s+(\d{4})\b",
            re.IGNORECASE,
        ),
        lambda m: _month_name_to_iso(m),
    ),
]

_MONTH_MAP: Dict[str, str] = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}


def _month_name_to_iso(match: re.Match) -> str:
    month = _MONTH_MAP[match.group(1).lower()]
    day = match.group(2).zfill(2)
    year = match.group(3)
    return f"{year}-{month}-{day}"


# ---------------------------------------------------------------------------
# Cleaning Result
# ---------------------------------------------------------------------------

@dataclass
class CleaningResult:
    """Holds the output of a single document cleaning pass."""
    cleaned_text: str
    content_hash: str
    has_pii: bool
    pii_detections: List[PIIRecord] = field(default_factory=list)
    headers_stripped: int = 0
    footers_stripped: int = 0
    chars_removed: int = 0
    original_length: int = 0


# ---------------------------------------------------------------------------
# Document Cleaner
# ---------------------------------------------------------------------------

class DocumentCleaner:
    """
    Production-grade document cleaner for knowledge base ingestion.

    Responsibilities:
    - Strip navigation artifacts (headers, footers, page numbers)
    - Normalize whitespace and headings
    - Standardize date formats to ISO 8601
    - Detect and mask PII in-place (replacing with typed placeholders)
    - Compute a SHA-256 content hash for deduplication
    """

    JACCARD_THRESHOLD: float = 0.85  # Documents above this threshold are near-duplicates

    def __init__(self, jaccard_threshold: float = 0.85) -> None:
        self.jaccard_threshold = jaccard_threshold
        self._seen_hashes: Set[str] = set()
        self._seen_shingles: List[Tuple[str, Set[str]]] = []  # (record_id, shingles)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clean(self, raw_text: str) -> CleaningResult:
        """
        Run the full cleaning pipeline on raw document text.

        Returns a CleaningResult with cleaned text, hash, and PII records.
        """
        original_length = len(raw_text)
        text = raw_text

        # Step 1: Strip headers and footers
        stripped_count, text = self._strip_header_footer(text)

        # Step 2: Normalize whitespace
        text = self._normalize_whitespace(text)

        # Step 3: Normalize dates to ISO 8601
        text = self._normalize_dates(text)

        # Step 4: Standardize headings (e.g. ALL CAPS → Title Case)
        text = self._normalize_headings(text)

        # Step 5: Detect and mask PII
        pii_records, text = self._detect_and_mask_pii(text)

        # Step 6: Final whitespace trim
        text = text.strip()

        # Step 7: Compute content hash
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        chars_removed = original_length - len(text)

        return CleaningResult(
            cleaned_text=text,
            content_hash=content_hash,
            has_pii=len(pii_records) > 0,
            pii_detections=pii_records,
            headers_stripped=stripped_count,
            chars_removed=max(0, chars_removed),
            original_length=original_length,
        )

    def is_near_duplicate(self, record_id: str, text: str) -> Optional[str]:
        """
        Check if `text` is a near-duplicate of any previously seen document.

        Uses character 4-grams (shingles) and Jaccard similarity.
        Returns the record_id of the canonical document if duplicate, else None.
        """
        shingles = self._shingle(text, n=4)
        for seen_id, seen_shingles in self._seen_shingles:
            similarity = self._jaccard(shingles, seen_shingles)
            if similarity >= self.jaccard_threshold:
                logger.info(
                    "Near-duplicate detected: '%s' ≈ '%s' (Jaccard=%.3f)",
                    record_id, seen_id, similarity,
                )
                return seen_id
        # Not a duplicate — register this document
        self._seen_shingles.append((record_id, shingles))
        return None

    def is_exact_duplicate(self, content_hash: str) -> bool:
        """Returns True if this hash was already seen (exact duplicate)."""
        if content_hash in self._seen_hashes:
            return True
        self._seen_hashes.add(content_hash)
        return False

    def reset(self) -> None:
        """Reset deduplication state (e.g. between ingestion runs)."""
        self._seen_hashes.clear()
        self._seen_shingles.clear()

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _strip_header_footer(self, text: str) -> Tuple[int, str]:
        """Remove common header/footer artifacts. Returns (count_stripped, cleaned_text)."""
        count = 0
        for pattern in _HEADER_FOOTER_PATTERNS:
            new_text, n = pattern.subn("", text)
            count += n
            text = new_text
        return count, text

    def _normalize_whitespace(self, text: str) -> str:
        """Collapse multiple blank lines to a single blank line; strip trailing spaces."""
        # Collapse 3+ blank lines → 2 blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Strip trailing whitespace per line
        text = "\n".join(line.rstrip() for line in text.splitlines())
        # Collapse multiple spaces/tabs within a line
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text

    def _normalize_dates(self, text: str) -> str:
        """Convert various date formats to ISO 8601 (YYYY-MM-DD)."""
        for pattern, repl in _DATE_PATTERNS:
            if callable(repl):
                text = pattern.sub(repl, text)
            else:
                text = pattern.sub(repl, text)
        return text

    def _normalize_headings(self, text: str) -> str:
        """
        Convert ALL-CAPS headings to Title Case and add consistent spacing.
        Detects lines that are fully uppercased with at least 4 characters.
        """
        lines = text.splitlines()
        normalized = []
        for line in lines:
            stripped = line.strip()
            if (
                len(stripped) >= 4
                and stripped.isupper()
                and not re.match(r"^\d+$", stripped)
            ):
                line = stripped.title()
            normalized.append(line)
        return "\n".join(normalized)

    def _detect_and_mask_pii(self, text: str) -> Tuple[List[PIIRecord], str]:
        """
        Scan text for PII patterns, build PIIRecord list, replace in text.

        Replacement tokens: [EMAIL_REDACTED], [PHONE_REDACTED], etc.
        """
        pii_records: List[PIIRecord] = []
        used_offsets: Set[Tuple[int, int]] = set()

        for pii_type, pattern in _PII_PATTERNS:
            for match in pattern.finditer(text):
                span = (match.start(), match.end())
                # Avoid double-counting overlapping matches
                if any(
                    s <= match.start() < e or s < match.end() <= e
                    for s, e in used_offsets
                ):
                    continue
                used_offsets.add(span)
                original = match.group(0)
                masked = f"[{pii_type.value.upper()}_REDACTED]"
                pii_records.append(
                    PIIRecord(
                        pii_type=pii_type,
                        original_value=original,
                        masked_value=masked,
                        char_offset=match.start(),
                        char_length=len(original),
                    )
                )

        # Apply all replacements (process in reverse order to preserve offsets)
        if pii_records:
            # Sort by offset descending for safe in-place replacement
            pii_records_sorted = sorted(pii_records, key=lambda r: r.char_offset, reverse=True)
            for record in pii_records_sorted:
                start = record.char_offset
                end = start + record.char_length
                text = text[:start] + record.masked_value + text[end:]

        return pii_records, text

    @staticmethod
    def _shingle(text: str, n: int = 4) -> Set[str]:
        """Generate character n-gram shingles for Jaccard similarity."""
        text = re.sub(r"\s+", " ", text.lower().strip())
        return {text[i : i + n] for i in range(len(text) - n + 1)}

    @staticmethod
    def _jaccard(set_a: Set[str], set_b: Set[str]) -> float:
        """Compute Jaccard similarity between two sets."""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

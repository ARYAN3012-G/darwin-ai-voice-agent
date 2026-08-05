"""
Q2 Knowledge Base — Schema Definitions
=======================================
Defines the canonical data models for all documents ingested into the
production-ready knowledge base. Uses Pydantic v2 for strict validation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DocumentCategory(str, Enum):
    """High-level taxonomy categories for knowledge documents."""
    PRODUCT = "product"
    POLICY = "policy"
    QUALIFICATION = "qualification"
    FAQ = "faq"
    OBJECTION = "objection"
    COMPLIANCE = "compliance"
    PRICING = "pricing"
    PROCESS = "process"
    ESCALATION = "escalation"


class DocumentStatus(str, Enum):
    """Lifecycle status of a knowledge record."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DRAFT = "draft"
    ARCHIVED = "archived"


class PIIType(str, Enum):
    """Types of PII that can be detected and masked."""
    EMAIL = "email"
    PHONE = "phone"
    TIN = "tin"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    NAME = "name"
    ADDRESS = "address"


# ---------------------------------------------------------------------------
# Core Data Models
# ---------------------------------------------------------------------------

class PIIRecord(BaseModel):
    """Tracks a single PII detection in a document."""
    pii_type: PIIType
    original_value: str
    masked_value: str
    char_offset: int
    char_length: int


class SourceTracking(BaseModel):
    """Full provenance record for a knowledge document."""
    source_url: Optional[str] = None
    source_file: Optional[str] = None
    source_system: str = "manual"
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    ingested_by: str = "knowledge_pipeline_v1"
    checksum_sha256: Optional[str] = None
    original_filename: Optional[str] = None
    page_numbers: Optional[List[int]] = None


class DocumentTaxonomy(BaseModel):
    """Fine-grained classification tags for retrieval filtering."""
    primary_category: DocumentCategory
    secondary_categories: List[DocumentCategory] = Field(default_factory=list)
    product_lines: List[str] = Field(default_factory=list)
    markets: List[str] = Field(default_factory=list)           # e.g. ["PH", "ID", "global"]
    applicable_roles: List[str] = Field(default_factory=list)  # e.g. ["agent", "underwriter"]
    keywords: List[str] = Field(default_factory=list)
    intent_tags: List[str] = Field(default_factory=list)       # e.g. ["objection_handling"]


class KnowledgeRecord(BaseModel):
    """
    Canonical knowledge base record representing a single chunk of
    cleaned, deduplicated, PII-masked content ready for retrieval.
    """
    record_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Globally unique identifier for this record.",
    )
    title: str = Field(description="Human-readable title for the record.")
    content: str = Field(description="Cleaned, PII-masked content body.")
    summary: str = Field(
        default="",
        description="One-sentence summary used for hybrid retrieval scoring.",
    )
    category: DocumentCategory
    taxonomy: DocumentTaxonomy
    source: SourceTracking = Field(default_factory=SourceTracking)
    version: str = Field(
        default="1.0.0",
        description="Semantic version of this record (major.minor.patch).",
    )
    status: DocumentStatus = Field(default=DocumentStatus.ACTIVE)
    has_pii: bool = Field(
        default=False,
        description="True if PII was detected before masking.",
    )
    pii_detections: List[PIIRecord] = Field(default_factory=list)
    duplicate_of: Optional[str] = Field(
        default=None,
        description="record_id of the canonical record if this is a near-duplicate.",
    )
    content_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of the cleaned content for deduplication.",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(f"Version must be in major.minor.patch format, got: {v}")
        return v

    def to_retrieval_text(self) -> str:
        """Returns concatenated text used during retrieval indexing."""
        keywords = " ".join(self.taxonomy.keywords)
        intent_tags = " ".join(self.taxonomy.intent_tags)
        return f"{self.title} {self.summary} {self.content} {keywords} {intent_tags}"

    def to_display_dict(self) -> Dict[str, Any]:
        """Returns a cleaned dictionary for API/dashboard display."""
        return {
            "record_id": self.record_id,
            "title": self.title,
            "summary": self.summary,
            "category": self.category.value,
            "version": self.version,
            "status": self.status.value,
            "has_pii": self.has_pii,
            "markets": self.taxonomy.markets,
            "product_lines": self.taxonomy.product_lines,
            "keywords": self.taxonomy.keywords,
            "source_system": self.source.source_system,
            "ingested_at": self.source.ingested_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# Search Result & Retrieval Report Models
# ---------------------------------------------------------------------------

class SearchResult(BaseModel):
    """A single ranked result returned by the hybrid retriever."""
    rank: int
    record_id: str
    title: str
    summary: str
    content_snippet: str
    category: str
    markets: List[str]
    bm25_score: float = 0.0
    dense_score: float = 0.0
    rrf_score: float = 0.0
    citation: str = Field(description="Human-readable citation string for the result.")

    def to_agent_context(self) -> str:
        """Formats result for injection into agent context window."""
        return (
            f"[Source: {self.citation}]\n"
            f"Category: {self.category.upper()}\n"
            f"{self.content_snippet}"
        )


class RetrievalReport(BaseModel):
    """Full report produced by the retrieval verification test suite."""
    query: str
    top_k: int
    total_indexed: int
    results: List[SearchResult]
    retrieval_time_ms: float
    verdict: str  # "PASS" | "PARTIAL" | "FAIL"
    notes: str = ""

    def summary_line(self) -> str:
        return (
            f"Query: '{self.query}' | "
            f"Results: {len(self.results)}/{self.top_k} | "
            f"Time: {self.retrieval_time_ms:.1f}ms | "
            f"Verdict: {self.verdict}"
        )

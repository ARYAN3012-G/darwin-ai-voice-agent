"""
Q2 Knowledge Base — Hybrid BM25 + Dense Retriever with RRF Fusion
===================================================================
Implements a production-grade hybrid retrieval pipeline:

  1. BM25 (Okapi BM25) — Sparse keyword matching
  2. TF-IDF Dense — Semantic-adjacent dense vector similarity
  3. Reciprocal Rank Fusion (RRF) — Merges both ranked lists

The combined approach ensures strong performance on:
  - Exact keyword queries (BM25 strength)
  - Paraphrased / semantic queries (Dense strength)
  - Mixed precision/recall trade-offs (RRF balancing)

All results include explicit citations and source tracking for
grounded response generation.
"""

from __future__ import annotations

import logging
import math
import re
import time
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from .cleaner import DocumentCleaner
from .knowledge_data import KNOWLEDGE_DOCUMENTS
from .schema import KnowledgeRecord, RetrievalReport, SearchResult
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BM25 Implementation
# ---------------------------------------------------------------------------

class BM25Index:
    """
    Okapi BM25 sparse retrieval index.

    Parameters:
        k1 (float): Term frequency saturation parameter (typically 1.2–2.0)
        b  (float): Length normalization parameter (typically 0.75)
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._record_ids: List[str] = []
        self._doc_lengths: List[int] = []
        self._avg_doc_length: float = 0.0
        self._inverted_index: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        # (doc_idx, term_freq) pairs
        self._vocabulary: set = set()

    def add_document(self, record_id: str, text: str) -> None:
        """Add a document to the BM25 index."""
        doc_idx = len(self._record_ids)
        self._record_ids.append(record_id)
        tokens = self._tokenize(text)
        self._doc_lengths.append(len(tokens))
        counts = Counter(tokens)
        for term, freq in counts.items():
            self._inverted_index[term].append((doc_idx, freq))
            self._vocabulary.add(term)

    def build(self) -> None:
        """Finalize the index by computing average document length."""
        if self._doc_lengths:
            self._avg_doc_length = sum(self._doc_lengths) / len(self._doc_lengths)
        logger.info(
            "BM25 index built: %d documents, %d unique terms, avg_len=%.1f",
            len(self._record_ids), len(self._vocabulary), self._avg_doc_length,
        )

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Return top-k (record_id, bm25_score) pairs for a query."""
        if not self._record_ids:
            return []

        query_tokens = self._tokenize(query)
        n_docs = len(self._record_ids)
        scores: Dict[int, float] = defaultdict(float)

        for term in query_tokens:
            if term not in self._inverted_index:
                continue
            postings = self._inverted_index[term]
            df = len(postings)
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)
            for doc_idx, tf in postings:
                doc_len = self._doc_lengths[doc_idx]
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * (doc_len / max(self._avg_doc_length, 1))
                )
                scores[doc_idx] += idf * (numerator / denominator)

        # Sort and return top-k
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            (self._record_ids[doc_idx], float(score))
            for doc_idx, score in sorted_results
        ]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple alphanumeric tokenizer with stopword removal."""
        _STOPWORDS = {
            "the", "a", "an", "in", "on", "at", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "should", "could", "may", "might", "must", "shall",
            "to", "of", "and", "or", "but", "for", "with", "by", "from",
            "this", "that", "these", "those", "it", "its", "not", "no",
        }
        tokens = re.findall(r"\b[a-zA-Z0-9]{2,}\b", text.lower())
        return [t for t in tokens if t not in _STOPWORDS]


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

def reciprocal_rank_fusion(
    *ranked_lists: List[Tuple[str, float]],
    k: int = 60,
) -> List[Tuple[str, float]]:
    """
    Merge multiple ranked lists using Reciprocal Rank Fusion.

    RRF score for document d across lists L1..Ln:
        RRF(d) = Σ 1 / (k + rank_i(d))

    k=60 is the standard value from the original RRF paper (Cormack 2009).
    Higher k reduces the sensitivity to top-ranked documents.
    """
    rrf_scores: Dict[str, float] = defaultdict(float)
    for ranked_list in ranked_lists:
        for rank, (record_id, _score) in enumerate(ranked_list, start=1):
            rrf_scores[record_id] += 1.0 / (k + rank)

    # Sort by descending RRF score
    merged = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return merged


# ---------------------------------------------------------------------------
# Hybrid Retriever
# ---------------------------------------------------------------------------

class HybridRetriever:
    """
    Production-ready hybrid retriever combining BM25 + TF-IDF Dense + RRF.

    Usage:
        retriever = HybridRetriever()
        retriever.build()
        results = retriever.search("What is the waiting period for health insurance?", top_k=3)
    """

    def __init__(
        self,
        documents: Optional[List[KnowledgeRecord]] = None,
        bm25_k1: float = 1.5,
        bm25_b: float = 0.75,
        rrf_k: int = 60,
    ) -> None:
        self._documents: Dict[str, KnowledgeRecord] = {}
        self._bm25 = BM25Index(k1=bm25_k1, b=bm25_b)
        self._dense = VectorStore()
        self._cleaner = DocumentCleaner()
        self._rrf_k = rrf_k
        self._is_built = False

        # Pre-clean and register all seed documents
        source_docs = documents or KNOWLEDGE_DOCUMENTS
        for doc in source_docs:
            self._register_document(doc)

    def build(self) -> None:
        """Build both BM25 and dense indexes. Call once after all documents are registered."""
        self._bm25.build()
        self._dense.build()
        self._is_built = True
        logger.info(
            "HybridRetriever built: %d documents indexed.", len(self._documents)
        )

    def add_document(self, record: KnowledgeRecord) -> None:
        """Register and index a new document at runtime."""
        self._register_document(record)
        if self._is_built:
            # Rebuild required when adding documents post-build
            self._dense.build()
            self._bm25.build()

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_category: Optional[str] = None,
        filter_market: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Execute hybrid retrieval for a query.

        Args:
            query: Natural language query string.
            top_k: Number of results to return.
            filter_category: Optional DocumentCategory value to filter results.
            filter_market: Optional market code (e.g. 'PH', 'ID') to filter.

        Returns:
            Ranked list of SearchResult objects with BM25, dense, and RRF scores.
        """
        if not self._is_built:
            self.build()

        # Run both retrievers with a wider candidate pool
        candidate_k = max(top_k * 3, 15)
        bm25_results = self._bm25.search(query, top_k=candidate_k)
        dense_results = self._dense.search(query, top_k=candidate_k)

        # Build score lookup maps
        bm25_scores: Dict[str, float] = dict(bm25_results)
        dense_scores: Dict[str, float] = dict(dense_results)

        # RRF fusion
        merged = reciprocal_rank_fusion(bm25_results, dense_results, k=self._rrf_k)

        # Apply optional filters and build SearchResult objects
        search_results: List[SearchResult] = []
        for record_id, rrf_score in merged:
            if record_id not in self._documents:
                continue
            doc = self._documents[record_id]

            # Category filter
            if filter_category and doc.category.value != filter_category.lower():
                continue
            # Market filter
            if filter_market and filter_market.upper() not in doc.taxonomy.markets:
                continue

            snippet = self._extract_snippet(doc.content, query)
            citation = self._build_citation(doc)

            search_results.append(
                SearchResult(
                    rank=len(search_results) + 1,
                    record_id=record_id,
                    title=doc.title,
                    summary=doc.summary,
                    content_snippet=snippet,
                    category=doc.category.value,
                    markets=doc.taxonomy.markets,
                    bm25_score=round(bm25_scores.get(record_id, 0.0), 4),
                    dense_score=round(dense_scores.get(record_id, 0.0), 4),
                    rrf_score=round(rrf_score, 6),
                    citation=citation,
                )
            )

            if len(search_results) >= top_k:
                break

        return search_results

    def search_and_report(self, query: str, top_k: int = 5) -> RetrievalReport:
        """Run search and wrap results in a RetrievalReport with timing."""
        start = time.perf_counter()
        results = self.search(query, top_k=top_k)
        elapsed_ms = (time.perf_counter() - start) * 1000

        verdict = "PASS" if results else "FAIL"
        if 0 < len(results) < top_k:
            verdict = "PARTIAL"

        return RetrievalReport(
            query=query,
            top_k=top_k,
            total_indexed=len(self._documents),
            results=results,
            retrieval_time_ms=round(elapsed_ms, 2),
            verdict=verdict,
        )

    def get_context_for_agent(self, query: str, top_k: int = 3) -> str:
        """
        Return formatted context string ready for injection into an LLM prompt.
        Grounded: always returns source citations so the agent can trace answers.
        """
        results = self.search(query, top_k=top_k)
        if not results:
            return "NO_CONTEXT_FOUND"

        context_blocks = []
        for result in results:
            context_blocks.append(result.to_agent_context())

        return "\n\n---\n\n".join(context_blocks)

    def total_documents(self) -> int:
        return len(self._documents)

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _register_document(self, record: KnowledgeRecord) -> None:
        """Clean and index a knowledge record into both BM25 and dense stores."""
        if record.record_id in self._documents:
            logger.warning("Duplicate record_id '%s' — skipping.", record.record_id)
            return

        # Clean the retrieval text
        retrieval_text = record.to_retrieval_text()
        cleaning_result = self._cleaner.clean(retrieval_text)

        self._documents[record.record_id] = record
        self._bm25.add_document(record.record_id, cleaning_result.cleaned_text)
        self._dense.add_document(record.record_id, cleaning_result.cleaned_text)

    @staticmethod
    def _extract_snippet(content: str, query: str, window: int = 300) -> str:
        """
        Extract the most relevant snippet from a document for display.
        Finds the highest-density query keyword region.
        """
        # Find the query tokens in the content
        query_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", query.lower()))
        content_lower = content.lower()

        best_start = 0
        best_count = 0

        for i in range(0, max(1, len(content) - window), 50):
            window_text = content_lower[i : i + window]
            count = sum(1 for tok in query_tokens if tok in window_text)
            if count > best_count:
                best_count = count
                best_start = i

        snippet = content[best_start : best_start + window].strip()
        if best_start > 0:
            snippet = "..." + snippet
        if best_start + window < len(content):
            snippet += "..."
        return snippet

    @staticmethod
    def _build_citation(doc: KnowledgeRecord) -> str:
        """Build a human-readable citation string for a document."""
        markets = ", ".join(doc.taxonomy.markets) if doc.taxonomy.markets else "Global"
        return (
            f"{doc.title} "
            f"[v{doc.version} | {doc.category.value.upper()} | Market: {markets}]"
        )

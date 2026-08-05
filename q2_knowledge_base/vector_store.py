"""
Q2 Knowledge Base — TF-IDF Dense Vector Store
================================================
Builds a lightweight dense vector index using TF-IDF representations.
Provides cosine similarity search without external embedding services,
making the system fully self-contained and testable offline.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class VectorStore:
    """
    TF-IDF based dense vector store with cosine similarity search.

    Documents are indexed by their retrieval text (title + summary + content
    + keywords + intent_tags) using a custom TF-IDF implementation that
    works without scikit-learn, falling back to it if available for better
    tokenization.

    Each indexed entry is identified by a record_id and stores:
      - The TF-IDF vector (numpy array)
      - The vocabulary mapping (term → index)
    """

    def __init__(self) -> None:
        self._record_ids: List[str] = []
        self._corpus_texts: List[str] = []
        self._tfidf_matrix: Optional[np.ndarray] = None  # shape: (n_docs, vocab_size)
        self._vocabulary: Dict[str, int] = {}
        self._idf_vector: Optional[np.ndarray] = None
        self._is_built: bool = False
        self._use_sklearn: bool = False
        self._sklearn_vectorizer = None  # sklearn TfidfVectorizer if available

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_document(self, record_id: str, text: str) -> None:
        """Register a document for indexing. Must call build() after all adds."""
        self._record_ids.append(record_id)
        self._corpus_texts.append(text.lower())
        self._is_built = False

    def build(self) -> None:
        """Build the TF-IDF index from all registered documents."""
        if not self._corpus_texts:
            logger.warning("VectorStore.build() called with no documents.")
            return

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=1,
                max_features=8000,
                sublinear_tf=True,
            )
            matrix = vectorizer.fit_transform(self._corpus_texts)
            self._tfidf_matrix = matrix.toarray().astype(np.float32)
            self._sklearn_vectorizer = vectorizer
            self._use_sklearn = True
            logger.info("VectorStore built with sklearn TF-IDF (%d docs, %d features).",
                        len(self._corpus_texts), self._tfidf_matrix.shape[1])
        except ImportError:
            logger.info("sklearn not available, using custom TF-IDF implementation.")
            self._build_custom_tfidf()

        self._is_built = True

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Return top-k (record_id, cosine_score) pairs for a query.
        Scores are in [0, 1] where 1 = perfect match.
        """
        if not self._is_built:
            self.build()

        if self._tfidf_matrix is None or len(self._record_ids) == 0:
            return []

        query_vec = self._vectorize_query(query.lower())
        if query_vec is None:
            return []

        scores = self._cosine_similarity_batch(query_vec, self._tfidf_matrix)
        ranked_indices = np.argsort(scores)[::-1]

        results: List[Tuple[str, float]] = []
        for idx in ranked_indices[:top_k]:
            score = float(scores[idx])
            if score > 0.0:
                results.append((self._record_ids[idx], score))

        return results

    def __len__(self) -> int:
        return len(self._record_ids)

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _vectorize_query(self, query: str) -> Optional[np.ndarray]:
        """Transform query text into a TF-IDF vector matching the corpus vocabulary."""
        if self._use_sklearn and self._sklearn_vectorizer is not None:
            vec = self._sklearn_vectorizer.transform([query]).toarray().astype(np.float32)
            return vec[0]

        # Custom TF-IDF query vectorization
        if not self._vocabulary or self._idf_vector is None:
            return None

        tokens = self._tokenize(query)
        tf = self._compute_tf(tokens)
        query_vec = np.zeros(len(self._vocabulary), dtype=np.float32)
        for term, tf_val in tf.items():
            if term in self._vocabulary:
                idx = self._vocabulary[term]
                query_vec[idx] = tf_val * self._idf_vector[idx]

        norm = np.linalg.norm(query_vec)
        if norm > 0:
            query_vec /= norm
        return query_vec

    def _build_custom_tfidf(self) -> None:
        """Pure-Python TF-IDF implementation as sklearn fallback."""
        # Build vocabulary from all documents
        tokenized_docs = [self._tokenize(text) for text in self._corpus_texts]
        vocab_set: set = set()
        for tokens in tokenized_docs:
            vocab_set.update(tokens)

        self._vocabulary = {term: idx for idx, term in enumerate(sorted(vocab_set))}
        vocab_size = len(self._vocabulary)
        n_docs = len(tokenized_docs)

        # Compute TF for each document
        tf_matrix = np.zeros((n_docs, vocab_size), dtype=np.float32)
        for doc_idx, tokens in enumerate(tokenized_docs):
            tf = self._compute_tf(tokens)
            for term, tf_val in tf.items():
                if term in self._vocabulary:
                    tf_matrix[doc_idx, self._vocabulary[term]] = tf_val

        # Compute IDF
        df = np.sum(tf_matrix > 0, axis=0).astype(np.float32)
        self._idf_vector = np.log((n_docs + 1) / (df + 1)) + 1.0

        # TF-IDF matrix (normalized)
        tfidf = tf_matrix * self._idf_vector
        norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._tfidf_matrix = (tfidf / norms).astype(np.float32)

        logger.info("Custom TF-IDF built: %d docs, %d vocab terms.", n_docs, vocab_size)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple whitespace + punctuation tokenizer."""
        import re
        tokens = re.findall(r"\b[a-z]{2,}\b", text.lower())
        # Add bigrams for richer representation
        bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
        return tokens + bigrams

    @staticmethod
    def _compute_tf(tokens: List[str]) -> Dict[str, float]:
        """Compute sublinear TF (log normalization)."""
        from collections import Counter
        counts = Counter(tokens)
        tf = {}
        for term, count in counts.items():
            tf[term] = 1 + math.log(count) if count > 0 else 0
        return tf

    @staticmethod
    def _cosine_similarity_batch(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
        """Vectorized cosine similarity between a query vector and a document matrix."""
        # Matrix rows are assumed to be L2-normalized (done at index time)
        scores = matrix @ query_vec
        query_norm = np.linalg.norm(query_vec)
        if query_norm > 0:
            scores /= query_norm
        return scores

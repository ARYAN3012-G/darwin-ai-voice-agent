"""
Q2 Knowledge Base — Retrieval Verification Test Suite
======================================================
Executes 5 representative test queries against the production knowledge base
and evaluates retrieval quality:

  Test 1: Product inquiry — Health Insurance coverage details
  Test 2: Policy / eligibility — Pre-existing conditions and waiting period
  Test 3: Qualification — Business loan financial requirements
  Test 4: FAQ — Claims filing process
  Test 5: Objection handling — "I can't afford the premium"

Each test checks that the correct category of document surfaces in the
top-3 results and reports retrieval time, scores, and a PASS/FAIL verdict.
"""

from __future__ import annotations

import logging
import sys
import time
from dataclasses import dataclass, field
from typing import List

# Ensure project root is on path when run directly
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from q2_knowledge_base.retriever import HybridRetriever
from q2_knowledge_base.schema import RetrievalReport

logging.basicConfig(level=logging.WARNING)


# ---------------------------------------------------------------------------
# Test Case Definitions
# ---------------------------------------------------------------------------

@dataclass
class TestCase:
    """Definition of a single retrieval test."""
    name: str
    query: str
    expected_categories: List[str]       # At least one result should match
    expected_keywords_in_snippet: List[str]  # At least one keyword in top result snippet
    min_rrf_score: float = 0.003         # Minimum acceptable RRF score for top result
    top_k: int = 3


TEST_CASES: List[TestCase] = [
    TestCase(
        name="T1 — Product Inquiry: Health Insurance Benefits",
        query="What are the benefits and coverage of comprehensive health insurance?",
        expected_categories=["product"],
        expected_keywords_in_snippet=["hospitalization", "outpatient", "coverage", "rider", "premium"],
        min_rrf_score=0.003,
    ),
    TestCase(
        name="T2 — Policy Inquiry: Pre-existing Conditions Waiting Period",
        query="What is the waiting period for pre-existing conditions in health insurance?",
        expected_categories=["qualification", "policy"],
        expected_keywords_in_snippet=["waiting period", "pre-existing", "30 days", "12 months", "exclusion"],
        min_rrf_score=0.003,
    ),
    TestCase(
        name="T3 — Qualification: Business Loan Financial Requirements",
        query="What are the financial ratio requirements to qualify for a business loan?",
        expected_categories=["qualification"],
        expected_keywords_in_snippet=["DSCR", "debt service", "ratio", "capital", "credit"],
        min_rrf_score=0.003,
    ),
    TestCase(
        name="T4 — FAQ: How to File an Insurance Claim",
        query="How do I file a claim for outpatient consultation or hospitalization?",
        expected_categories=["faq"],
        expected_keywords_in_snippet=["claim", "receipt", "medical records", "30 days", "outpatient"],
        min_rrf_score=0.003,
    ),
    TestCase(
        name="T5 — Objection Handling: Cannot Afford the Premium",
        query="The insurance premium is too expensive for me. I can't afford it.",
        expected_categories=["objection"],
        expected_keywords_in_snippet=["too expensive", "cost", "affordable", "PHP", "plan"],
        min_rrf_score=0.003,
    ),
]


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    """Result of a single test case execution."""
    test_name: str
    query: str
    verdict: str  # "PASS" | "FAIL" | "PARTIAL"
    retrieval_report: RetrievalReport
    category_match: bool
    keyword_match: bool
    score_ok: bool
    top_result_title: str = ""
    top_result_citation: str = ""
    notes: List[str] = field(default_factory=list)


def run_test(retriever: HybridRetriever, test: TestCase) -> TestResult:
    """Execute a single test case and return a structured result."""
    report = retriever.search_and_report(test.query, top_k=test.top_k)

    if not report.results:
        return TestResult(
            test_name=test.name,
            query=test.query,
            verdict="FAIL",
            retrieval_report=report,
            category_match=False,
            keyword_match=False,
            score_ok=False,
            notes=["No results returned."],
        )

    top_result = report.results[0]

    # Check 1: Expected category appears in top-k results
    returned_categories = {r.category for r in report.results}
    category_match = any(cat in returned_categories for cat in test.expected_categories)

    # Check 2: At least one expected keyword appears in any snippet
    all_snippets = " ".join(r.content_snippet.lower() for r in report.results)
    keyword_match = any(
        kw.lower() in all_snippets for kw in test.expected_keywords_in_snippet
    )

    # Check 3: Top result RRF score meets minimum threshold
    score_ok = top_result.rrf_score >= test.min_rrf_score

    # Determine verdict
    if category_match and keyword_match and score_ok:
        verdict = "PASS"
    elif category_match or keyword_match:
        verdict = "PARTIAL"
    else:
        verdict = "FAIL"

    notes = []
    if not category_match:
        notes.append(
            f"Expected category(ies) {test.expected_categories} not in top-k. "
            f"Got: {list(returned_categories)}"
        )
    if not keyword_match:
        notes.append(f"None of {test.expected_keywords_in_snippet[:3]} found in snippets.")
    if not score_ok:
        notes.append(
            f"Top RRF score {top_result.rrf_score:.6f} < threshold {test.min_rrf_score}"
        )

    return TestResult(
        test_name=test.name,
        query=test.query,
        verdict=verdict,
        retrieval_report=report,
        category_match=category_match,
        keyword_match=keyword_match,
        score_ok=score_ok,
        top_result_title=top_result.title,
        top_result_citation=top_result.citation,
        notes=notes,
    )


def print_separator(char: str = "─", width: int = 70) -> None:
    print(char * width)


def print_test_result(result: TestResult) -> None:
    """Pretty-print a single test result."""
    verdict_colors = {"PASS": "\033[92m", "PARTIAL": "\033[93m", "FAIL": "\033[91m"}
    reset = "\033[0m"
    color = verdict_colors.get(result.verdict, "")

    print(f"\n{color}▶ {result.test_name}{reset}")
    print(f"  Query   : {result.query}")
    print(f"  Verdict : {color}{result.verdict}{reset}")
    print(f"  Checks  : Category={'✓' if result.category_match else '✗'}  "
          f"Keywords={'✓' if result.keyword_match else '✗'}  "
          f"Score={'✓' if result.score_ok else '✗'}")
    print(f"  Top Hit : {result.top_result_title}")
    print(f"  Citation: {result.top_result_citation}")
    print(f"  Timing  : {result.retrieval_report.retrieval_time_ms:.1f}ms")

    if result.retrieval_report.results:
        print(f"\n  Ranked Results ({len(result.retrieval_report.results)}):")
        for r in result.retrieval_report.results:
            print(
                f"    [{r.rank}] {r.title[:55]:<55} "
                f"BM25={r.bm25_score:.4f}  Dense={r.dense_score:.4f}  "
                f"RRF={r.rrf_score:.6f}"
            )
        # Show snippet from top result
        top = result.retrieval_report.results[0]
        snippet_preview = top.content_snippet[:200].replace("\n", " ")
        print(f"\n  Snippet : {snippet_preview}...")

    if result.notes:
        print(f"\n  Notes:")
        for note in result.notes:
            print(f"    ⚠ {note}")


def run_all_tests() -> None:
    """Build the retriever and execute all test cases."""
    print_separator("═")
    print("  Q2 KNOWLEDGE BASE — RETRIEVAL VERIFICATION SUITE")
    print_separator("═")
    print(f"  Test Cases : {len(TEST_CASES)}")
    print(f"  Timestamp  : {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")

    # Initialize and build the retriever
    print("\n  Initializing HybridRetriever...")
    build_start = time.perf_counter()
    retriever = HybridRetriever()
    retriever.build()
    build_time = (time.perf_counter() - build_start) * 1000
    print(f"  Index built in {build_time:.1f}ms | Documents: {retriever.total_documents()}")
    print_separator()

    # Run all tests
    results: List[TestResult] = []
    for test_case in TEST_CASES:
        result = run_test(retriever, test_case)
        results.append(result)
        print_test_result(result)
        print_separator()

    # Summary
    passed = sum(1 for r in results if r.verdict == "PASS")
    partial = sum(1 for r in results if r.verdict == "PARTIAL")
    failed = sum(1 for r in results if r.verdict == "FAIL")
    avg_time = sum(r.retrieval_report.retrieval_time_ms for r in results) / len(results)

    print(f"\n{'═'*70}")
    print(f"  SUMMARY")
    print(f"  {'─'*66}")
    print(f"  PASS    : {passed}/{len(results)}")
    print(f"  PARTIAL : {partial}/{len(results)}")
    print(f"  FAIL    : {failed}/{len(results)}")
    print(f"  Avg Time: {avg_time:.1f}ms per query")
    overall = "✅ ALL PASSED" if passed == len(results) else (
        "⚠️  PARTIAL SUCCESS" if failed == 0 else "❌ SOME FAILURES"
    )
    print(f"\n  Overall : {overall}")
    print(f"{'═'*70}\n")

    # Also demonstrate grounded context extraction for an agent
    print("  BONUS: Grounded Context Extraction (for agent use)")
    print_separator()
    demo_query = "What documents do I need for a business loan application?"
    print(f"  Query: {demo_query}\n")
    context = retriever.get_context_for_agent(demo_query, top_k=2)
    print(context)
    print(f"\n{'═'*70}")


if __name__ == "__main__":
    run_all_tests()

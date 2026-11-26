"""Unit tests for benchmark truth gate checks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from audit_benchmark_truth import check_m3, check_ragas  # noqa: E402


REQUIRED = {
    "id", "query", "complexity", "provider", "latency_ms", "retrieval_hit",
    "citation_hit", "refusal_hit", "answer_hit", "expected_docs",
    "expected_pages", "out_of_scope",
}


def _query(out_of_scope: bool = False, hit: bool = True) -> dict:
    return {
        "id": "GT-01",
        "query": "test",
        "complexity": "simple",
        "provider": "legacy",
        "latency_ms": 1.0,
        "retrieval_hit": False if out_of_scope else hit,
        "citation_hit": False if out_of_scope else hit,
        "refusal_hit": False,
        "answer_hit": hit,
        "expected_docs": ["out_of_scope" if out_of_scope else "doc"],
        "expected_pages": {"doc": 1},
        "out_of_scope": out_of_scope,
    }


def _report(queries: list[dict], status: str = "PASS") -> dict:
    total = len(queries)
    return {
        "schema_version": 2,
        "migrated_from_legacy": True,
        "status": status,
        "metrics": {
            "retrieval_accuracy_pct": round(sum(q["retrieval_hit"] for q in queries) / total * 100, 2),
            "exact_citation_accuracy_pct": round(sum(q["citation_hit"] for q in queries) / total * 100, 2),
            "answer_faithfulness_accuracy_pct": round(sum(q["answer_hit"] for q in queries) / total * 100, 2),
        },
        "thresholds": {
            "retrieval_accuracy_min": 85.0,
            "exact_citation_accuracy_min": 80.0,
            "answer_faithfulness_min": 75.0,
        },
        "query_results": queries,
    }


def test_clean_ragas_report_passes():
    out_of_scope = _query(out_of_scope=True)
    out_of_scope["refusal_hit"] = True
    queries = [_query() for _ in range(9)] + [out_of_scope]
    assert check_ragas(_report(queries)) == []
    assert REQUIRED.issubset(set(_query()))


def test_wrong_status_is_detected():
    errors = check_ragas(_report([_query(), _query()], status="FAIL"))
    assert "ragas_status_mismatch" in errors


def test_out_of_scope_auto_hit_is_detected():
    bad = _query(out_of_scope=True)
    bad["retrieval_hit"] = True
    assert "ragas_out_of_scope_autohit" in check_ragas(_report([bad, _query()]))


def test_missing_out_of_scope_case_is_detected():
    assert "ragas_no_out_of_scope_case" in check_ragas(_report([_query(), _query()]))


def test_empty_expected_docs_is_detected():
    bad = _query(out_of_scope=True)
    bad["expected_docs"] = [""]
    errors = check_ragas(_report([_query(), bad]))
    assert "ragas_empty_expected_docs" in errors


def test_m3_overall_passed_formula():
    summary = {
        "eval_passed": True,
        "status_ttft_under_1s": True,
        "citations_under_1s": False,
        "overall_passed": False,
    }
    assert check_m3({"schema_version": 2, "summary": summary}) == []
    summary["overall_passed"] = True
    assert "m3_overall_passed_mismatch" in check_m3({"schema_version": 2, "summary": summary})

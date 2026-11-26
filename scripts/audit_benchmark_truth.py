"""Gate: benchmark artifacts must match the current honest contract and the corpus."""

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_processed_data import check_number_lock  # noqa: E402

RAGAS_PATH = ROOT / "data/benchmarks/ragas_milestone2_report.json"
M3_PATH = ROOT / "data/benchmark_milestone3_report.json"
OCR_PATH = ROOT / "data/benchmarks/ocr_comparison/qwen3_vl_4b_report.json"
GEMINI_PATH = ROOT / "data/benchmarks/ocr_comparison/gemini_auditor_report.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check_ragas(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != 2 or not isinstance(report.get("migrated_from_legacy"), bool):
        errors.append("ragas_schema")
    queries = report.get("query_results", [])
    required = {"id", "query", "complexity", "provider", "latency_ms", "retrieval_hit",
                "citation_hit", "refusal_hit", "answer_hit", "expected_docs",
                "expected_pages", "out_of_scope"}
    if any(not required.issubset(set(q)) for q in queries):
        errors.append("ragas_query_fields")
    if any(q.get("out_of_scope") and (q.get("retrieval_hit") or q.get("citation_hit")) for q in queries):
        errors.append("ragas_out_of_scope_autohit")
    if not any(q.get("out_of_scope") for q in queries):
        errors.append("ragas_no_out_of_scope_case")
    if any(not q.get("expected_docs") or not q["expected_docs"][0] for q in queries):
        errors.append("ragas_empty_expected_docs")
    metrics = report.get("metrics", {})
    total = len(queries) or 1
    recomputed = {
        "retrieval_accuracy_pct": round(sum(bool(q.get("retrieval_hit")) for q in queries) / total * 100, 2),
        "exact_citation_accuracy_pct": round(sum(bool(q.get("citation_hit")) for q in queries) / total * 100, 2),
        "answer_faithfulness_accuracy_pct": round(sum(bool(q.get("answer_hit")) for q in queries) / total * 100, 2),
    }
    for key, value in recomputed.items():
        if abs(float(metrics.get(key, -1)) - value) > 0.01:
            errors.append(f"ragas_metrics_mismatch:{key}")
    thresholds = report.get("thresholds", {})
    passed = (
        metrics.get("retrieval_accuracy_pct", 0) >= thresholds.get("retrieval_accuracy_min", 85)
        and metrics.get("exact_citation_accuracy_pct", 0) >= thresholds.get("exact_citation_accuracy_min", 80)
        and metrics.get("answer_faithfulness_accuracy_pct", 0) >= thresholds.get("answer_faithfulness_min", 75)
    )
    expected_status = "PASS" if passed else "FAIL"
    if report.get("status") != expected_status:
        errors.append("ragas_status_mismatch")
    return errors


def check_m3(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema_version") != 2:
        errors.append("m3_schema")
    summary = report.get("summary", {})
    expected = bool(
        summary.get("eval_passed")
        and summary.get("status_ttft_under_1s")
        and summary.get("citations_under_1s")
    )
    if summary.get("overall_passed") is not expected:
        errors.append("m3_overall_passed_mismatch")
    return errors


def check_ocr(report: dict[str, Any], corpus: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("summary", {}).get("total_rectified") != corpus["rectified"]:
        errors.append("ocr_rectified_count")
    if report.get("summary", {}).get("total_tables") != corpus["tables"]:
        errors.append("ocr_table_count")
    if report.get("models") != corpus["models"]:
        errors.append("ocr_models")
    if report.get("summary", {}).get("safeguard_breaches_in_corpus") != corpus["breaches"]:
        errors.append("ocr_breaches")
    return errors


def check_gemini(report: dict[str, Any], corpus_gemini_count: int) -> list[str]:
    errors: list[str] = []
    if report.get("verified_count") != corpus_gemini_count:
        errors.append("gemini_count")
    if "ground-truth cross-check" in json.dumps(report, ensure_ascii=True).lower():
        errors.append("gemini_ground_truth_claim")
    return errors


def _corpus_stats() -> dict[str, Any]:
    tables = []
    for file_path in sorted((ROOT / "data/processed").glob("*.json")):
        data = json.loads(file_path.read_text(encoding="utf-8"))
        tables.extend(n for n in data.get("nodes", []) if n.get("level") == "TABLE")
    from collections import Counter

    models = Counter(
        str(n.get("metadata", {}).get("rectified_model", "unknown")) for n in tables
    )
    breaches = sum(
        1 for n in tables
        if not check_number_lock(n.get("metadata", {}).get("raw_content_backup"), n.get("content", ""))[0]
    )
    return {
        "tables": len(tables),
        "rectified": sum(1 for n in tables if n.get("metadata", {}).get("vlm_rectified")),
        "models": dict(models),
        "breaches": breaches,
        "gemini": sum(1 for k, v in models.items() if "gemini" in k.lower() for _ in range(v)),
    }


def main() -> int:
    errors: list[str] = []
    ragas = _load(RAGAS_PATH)
    errors.extend(check_ragas(ragas))
    errors.extend(check_m3(_load(M3_PATH)))
    corpus = _corpus_stats()
    errors.extend(check_ocr(_load(OCR_PATH), corpus))
    errors.extend(check_gemini(_load(GEMINI_PATH), corpus["gemini"]))

    summary = {
        "ragas_status": ragas.get("status"),
        "ragas_metrics": ragas.get("metrics"),
        "m3_overall_passed": _load(M3_PATH).get("summary", {}).get("overall_passed"),
        "corpus_tables": corpus["tables"],
        "corpus_rectified": corpus["rectified"],
        "errors": errors,
    }
    print(json.dumps(summary, ensure_ascii=True))
    print("BENCHMARK TRUTH PASS" if not errors else "BENCHMARK TRUTH FAIL")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

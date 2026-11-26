"""Migrate legacy benchmark artifacts to the current honest contract (no LLM calls)."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAGAS_PATH = ROOT / "data" / "benchmarks" / "ragas_milestone2_report.json"
M3_PATH = ROOT / "data" / "benchmark_milestone3_report.json"
LEGACY_M3_PATH = M3_PATH
NOW = datetime.now(timezone.utc).isoformat()


def _write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        tmp_path = Path(handle.name)
    os.replace(tmp_path, path)


def migrate_ragas() -> None:
    source_path = Path(os.getenv("RAGAS_LEGACY_SOURCE", str(RAGAS_PATH)))
    old = json.loads(source_path.read_text(encoding="utf-8"))
    queries = []
    for item in old.get("query_results", []):
        expected_doc = item.get("expected_doc") or (item.get("expected_docs") or [""])[0]
        out_of_scope = bool(item.get("out_of_scope")) or expected_doc == "out_of_scope"
        queries.append({
            "id": item.get("id"),
            "query": item.get("query"),
            "complexity": "legacy",
            "provider": "legacy",
            "latency_ms": old["metrics"]["average_latency_ms"],
            "expected_docs": [expected_doc],
            "expected_pages": {expected_doc: item.get("expected_page", 0)},
            "retrieval_hit": False if out_of_scope else bool(item.get("retrieval_hit")),
            "citation_hit": False if out_of_scope else bool(item.get("citation_hit")),
            "refusal_hit": False,
            "answer_hit": bool(item.get("answer_hit")),
            "out_of_scope": out_of_scope,
            "latency_is_per_query": False,
        })

    total = len(queries) or 1
    metrics = {
        "retrieval_accuracy_pct": round(sum(q["retrieval_hit"] for q in queries) / total * 100, 2),
        "exact_citation_accuracy_pct": round(sum(q["citation_hit"] for q in queries) / total * 100, 2),
        "answer_faithfulness_accuracy_pct": round(sum(q["answer_hit"] for q in queries) / total * 100, 2),
        "average_latency_ms": old["metrics"]["average_latency_ms"],
    }
    thresholds = old.get("thresholds", {})
    passed = (
        metrics["retrieval_accuracy_pct"] >= thresholds.get("retrieval_accuracy_min", 85)
        and metrics["exact_citation_accuracy_pct"] >= thresholds.get("exact_citation_accuracy_min", 80)
        and metrics["answer_faithfulness_accuracy_pct"] >= thresholds.get("answer_faithfulness_min", 75)
    )
    migrated = {
        "schema_version": 2,
        "migrated_from_legacy": True,
        "migrated_at": NOW,
        "original_timestamp": old.get("original_timestamp") or old.get("timestamp"),
        "migration_note": "Schema migrated; out_of_scope auto-hits removed. No new LLM queries were run.",
        "milestone": old.get("milestone", "2"),
        "benchmark_name": old.get("benchmark_name"),
        "total_queries": len(queries),
        "metrics": metrics,
        "thresholds": thresholds,
        "status": "PASS" if passed else "FAIL",
        "query_results": queries,
    }
    _write_atomic(RAGAS_PATH, migrated)


def migrate_m3() -> None:
    source = M3_PATH if M3_PATH.exists() else LEGACY_M3_PATH
    old = json.loads(source.read_text(encoding="utf-8"))
    summary = old.get("summary", {})
    eval_passed = summary.get("eval_passed", summary.get("overall_passed", False))
    status_ttft = bool(summary.get("status_ttft_under_1s", False))
    citations_ttft = bool(summary.get("citations_under_1s", False))
    overall_passed = bool(eval_passed and status_ttft and citations_ttft)

    summary.pop("frontend_verified", None)
    summary.pop("hitl_interface_ready", None)
    summary["eval_passed"] = bool(eval_passed)
    summary["overall_passed"] = overall_passed
    migrated = {
        "schema_version": 2,
        "migrated_from_legacy": True,
        "migrated_at": NOW,
        "benchmark": old.get("benchmark", "milestone3"),
        "timestamp": old.get("timestamp"),
        "summary": summary,
        "multi_persona_eval": old.get("multi_persona_eval", {}),
        "latency_profiles": old.get("latency_profiles", []),
        "migration_note": "overall_passed now includes both status TTFT and real citations latency. No benchmark re-run.",
    }
    _write_atomic(M3_PATH, migrated)


def main() -> None:
    migrate_ragas()
    migrate_m3()
    print("Migrated RAGAS and M3 benchmark artifacts to schema_version=2 (no LLM calls)")


if __name__ == "__main__":
    main()

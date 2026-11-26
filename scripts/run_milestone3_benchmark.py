"""Benchmark & Quality Evaluation Script for Milestone 3 (Scan2RAG).

Runs:
1. Multi-Persona Evaluation (Data Pipeline, OCR Vision, Legal Domain).
2. End-to-End Latency & SSE Time-to-First-Token (TTFT) profiling on legal queries.
3. Outputs comprehensive artifact to data/benchmark_milestone3_report.json.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

# Ensure backend app is on sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.evaluation.multi_persona_evaluator import MultiPersonaEvaluator
from app.services.qa_service import GroundedQAService
from app.retrieval.bm25_searcher import LegalBM25Searcher
from app.retrieval.hybrid_searcher import LegalHybridSearcher
from app.retrieval.qdrant_client import LegalVectorStore
from app.retrieval.reranker import LegalReranker

TEST_QUERIES = [
    "Cận thị từ -3D đến dưới -4D khám nghĩa vụ quân sự mấy điểm?",
    "Loạn thị có được tạm hoãn nghĩa vụ quân sự không?",
    "Tiêu chuẩn chỉ số khối cơ thể BMI trong tuyển chọn nghĩa vụ quân sự?",
]


def run_benchmark():
    print("=" * 65)
    print("       SCAN2RAG MILESTONE 3 AGENTIC BENCHMARK & EVALUATION       ")
    print("=" * 65)

    # 1. Multi-Persona Evaluation
    print("\n[1/3] Running Agentic Multi-Persona Evaluator...")
    evaluator = MultiPersonaEvaluator()
    eval_results = evaluator.evaluate_all()

    pipeline_res = eval_results["personas"]["data_pipeline"]
    vision_res = eval_results["personas"]["ocr_vision"]
    legal_res = eval_results["personas"]["legal_domain"]

    print(f"  • Data Pipeline Auditor : Score {pipeline_res['score']}/100 | Passed: {pipeline_res['passed']}")
    print(f"  • OCR Vision Auditor     : Score {vision_res['score']}/100 | Passed: {vision_res['passed']}")
    print(f"  • Legal Domain Auditor   : Score {legal_res['score']}/100 | Passed: {legal_res['passed']}")
    print(f"  ⭐ OVERALL QUALITY SCORE : {eval_results['overall_quality_score']}/100")

    # 2. End-to-End TTFT & SSE Latency Profiling
    print("\n[2/3] Measuring End-to-End Latency & Time-to-First-Token (TTFT)...")
    vector_store = LegalVectorStore(collection_name="vietnamese_legal_docs")
    bm25_searcher = LegalBM25Searcher()
    bm25_searcher.load()
    hybrid_searcher = LegalHybridSearcher(vector_store=vector_store, bm25_searcher=bm25_searcher)
    reranker = LegalReranker()
    qa_service = GroundedQAService(hybrid_searcher=hybrid_searcher, reranker=reranker)

    # Warmup retrieval + reranker once before timing
    for _ in qa_service.stream_answer_query("warmup", top_k_retrieval=5, top_k_rerank=1):
        break

    latency_records = []
    for query in TEST_QUERIES:
        start_t = time.perf_counter()
        stream_gen = qa_service.stream_answer_query(query, top_k_retrieval=15, top_k_rerank=5)
        ttft_status_ms = None
        citations_latency_ms = None
        citations_count = 0

        for chunk_str in stream_gen:
            elapsed_ms = (time.perf_counter() - start_t) * 1000
            for line in chunk_str.split("\n"):
                if line.startswith("data:"):
                    try:
                        event = json.loads(line.replace("data:", "").strip())
                        if event.get("event") == "status" and ttft_status_ms is None:
                            ttft_status_ms = elapsed_ms
                        elif event.get("event") == "citations":
                            citations_count = len(event.get("citations", []))
                            citations_latency_ms = elapsed_ms
                            if ttft_status_ms is None:
                                ttft_status_ms = elapsed_ms
                    except Exception:
                        pass
            if citations_count > 0:
                break

        total_time_ms = (time.perf_counter() - start_t) * 1000
        latency_records.append({
            "query": query,
            "ttft_status_ms": round(ttft_status_ms, 1) if ttft_status_ms is not None else round(total_time_ms, 1),
            "citations_latency_ms": round(citations_latency_ms, 1) if citations_latency_ms is not None else round(total_time_ms, 1),
            "citations_found": citations_count,
        })
        print(
            f"  Query: '{query[:35]}...' -> TTFT(status): {latency_records[-1]['ttft_status_ms']} ms | "
            f"Citations: {latency_records[-1]['citations_latency_ms']} ms ({citations_count} items)"
        )

    avg_ttft = round(sum(r["ttft_status_ms"] for r in latency_records) / len(latency_records), 1)
    avg_citations_ms = round(sum(r["citations_latency_ms"] for r in latency_records) / len(latency_records), 1)
    print(f"\n  ⚡ Average TTFT (first SSE event): {avg_ttft} ms | Average Citations Latency: {avg_citations_ms} ms")

    # 3. Save Milestone 3 Report
    print("\n[3/3] Saving Milestone 3 Report Artifact...")
    report = {
        "schema_version": 2,
        "migrated_from_legacy": False,
        "milestone": "Milestone 3",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "overall_quality_score": eval_results["overall_quality_score"],
            "eval_passed": eval_results["overall_passed"],
            "overall_passed": (
                eval_results["overall_passed"]
                and avg_ttft < 1000.0
                and avg_citations_ms < 1000.0
            ),
            "avg_ttft_status_ms": avg_ttft,
            "avg_citations_latency_ms": avg_citations_ms,
            "status_ttft_under_1s": avg_ttft < 1000.0,
            "citations_under_1s": avg_citations_ms < 1000.0,
        },
        "multi_persona_eval": eval_results,
        "latency_profiles": latency_records,
    }

    report_path = root_dir / "data" / "benchmark_milestone3_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"  ✓ Saved to: {report_path.relative_to(root_dir)}")
    print("=" * 65)
    print("🎉 MILESTONE 3 BENCHMARK & MULTI-PERSONA AUDIT: COMPLETE")
    print("=" * 65)


if __name__ == "__main__":
    run_benchmark()

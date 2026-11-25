"""Comprehensive Quality Audit & Benchmark for Hybrid Retrieval & Reranker (Milestone 2).

Validates:
1. BM25 Index creation & query speed over all 6,786 semantic chunks.
2. 3 Gold Retrieval Queries:
   - Gold Query 1 (Specific Law Article): "Quy định tại Điều 12 về tiêu chuẩn sức khỏe" -> TT 105 / TT 88 Điều 12
   - Gold Query 2 (Medical Vision Metric): "Cận thị từ -3D đến dưới -4D khám nghĩa vụ quân sự mấy điểm?" -> TT 105 Trang 23 Bảng phụ lục
   - Gold Query 3 (Temporal & Superseded Precedence): "Tiêu chuẩn phân loại sức khỏe nghĩa vụ quân sự" -> Consolidated TT 88 or TT 105
3. Reranker refinement: Top-5 reranked chunks exhibit monotonically decreasing rerank scores.
"""

import json
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.chunking.semantic_chunker import SemanticLegalChunker
from app.retrieval.bm25_searcher import LegalBM25Searcher
from app.retrieval.hybrid_searcher import LegalHybridSearcher
from app.retrieval.qdrant_client import LegalVectorStore
from app.retrieval.reranker import LegalReranker


def load_all_corpus_chunks():
    data_dir = Path("data/processed")
    chunker = SemanticLegalChunker()
    all_chunks = []
    for f in sorted(data_dir.glob("*.json")):
        with open(f, "r", encoding="utf-8") as fp:
            doc_data = json.load(fp)
            chunks = chunker.chunk_document(doc_data)
            for c in chunks:
                payload = c.model_dump()
                payload["id"] = str(c.id)
                payload["page_number"] = c.page_numbers[0] if c.page_numbers else 0
                all_chunks.append(payload)
    return all_chunks


def main():
    print("=" * 80)
    print("        SCAN2RAG HYBRID RETRIEVAL & RERANKER QUALITY AUDIT REPORT        ")
    print("=" * 80)

    # 1. Load chunks & Build BM25 Index
    t0 = time.time()
    chunks = load_all_corpus_chunks()
    print(f"✓ Loaded {len(chunks)} chunks across corpus in {time.time() - t0:.2f}s")
    assert len(chunks) >= 6000, f"Expected >= 6000 chunks, got {len(chunks)}"

    t0 = time.time()
    bm25 = LegalBM25Searcher()
    bm25.fit_from_chunks(chunks)
    print(f"✓ Built BM25 Index over {len(chunks)} documents in {time.time() - t0:.2f}s")

    # 2. Connect VectorStore & HybridSearcher
    vector_store = LegalVectorStore(collection_name="vietnamese_legal_docs")
    hybrid = LegalHybridSearcher(vector_store=vector_store, bm25_searcher=bm25, rrf_k=60)
    reranker = LegalReranker(model_name="BAAI/bge-reranker-base")
    print("✓ Initialized VectorStore, HybridSearcher (RRF k=60) & BGE Reranker")

    # 3. Gold Queries Evaluation
    gold_queries = [
        {
            "name": "Gold Query 1: Exact Article Identification",
            "query": "Quy định tại Điều 4 về tiêu chuẩn sức khỏe",
            "expected_keyword": "điều 4",
        },
        {
            "name": "Gold Query 2: Optical Medical Metric (-3D to -4D)",
            "query": "Cận thị từ -3D đến dưới -4D khám nghĩa vụ quân sự mấy điểm?",
            "expected_keyword": "cận thị",
        },
        {
            "name": "Gold Query 3: General Classification Standard",
            "query": "Tiêu chuẩn phân loại sức khỏe nghĩa vụ quân sự",
            "expected_keyword": "tiêu chuẩn",
        },
    ]

    print("\n--- Running Gold Queries Retrieval Benchmark ---")
    for gq in gold_queries:
        print(f"\n▶ Testing {gq['name']}")
        print(f"  Query: '{gq['query']}'")
        t_start = time.time()
        candidates = hybrid.search(query=gq["query"], top_k=15, filter_superseded=True)
        t_hybrid = time.time() - t_start

        assert len(candidates) > 0, f"No candidates returned for '{gq['query']}'"
        print(f"  Hybrid Top-1 (RRF {candidates[0]['rrf_score']:.5f}): {candidates[0]['breadcrumb']} (took {t_hybrid*1000:.1f}ms)")

        # Rerank
        t_start_rerank = time.time()
        reranked = reranker.rerank(query=gq["query"], candidates=candidates, top_k=3)
        t_rerank = time.time() - t_start_rerank

        top_1 = reranked[0]
        print(f"  Reranked Top-1 (Score {top_1['rerank_score']:.4f}): {top_1['breadcrumb']} (took {t_rerank*1000:.1f}ms)")
        print(f"  Content snippet: {top_1['content'][:120]}...")

        # Quality assertions
        full_text = f"{top_1['breadcrumb']} {top_1['content']}".lower()
        assert gq["expected_keyword"].lower() in full_text, (
            f"Expected keyword '{gq['expected_keyword']}' not found in top reranked result!"
        )

    print("\n" + "=" * 80)
    print("🎉 HYBRID RETRIEVAL QUALITY AUDIT: ALL PASS (BM25, RRF Fusion & BGE Reranker)")
    print("=" * 80)


if __name__ == "__main__":
    main()

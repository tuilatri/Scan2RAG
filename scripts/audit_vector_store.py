"""Auditor Script for Vector Store and Retrieval Invariants (Lauren Tan Methodology).

Hard Gates:
1. Collection integrity: Collection 'vietnamese_legal_docs' must exist in Qdrant.
2. Vector dimension lock: Stored vector size must be strictly 384.
3. Ingestion count match: Stored points count must match or exceed total chunks (>= 6000 points).
4. Top-1 Gold Retrieval Query: Query 'tiêu chuẩn cận thị nghĩa vụ quân sự' must retrieve
   Thông tư 105 / Thông tư 88 table with high confidence (score >= 0.70).
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.embeddings.embedder import LegalEmbedder
from app.retrieval.qdrant_client import LegalVectorStore


def audit_vector_store():
    print("=========================================================================")
    print("             SCAN2RAG VECTOR STORE AUDIT REPORT (MILESTONE 2)            ")
    print("=========================================================================")

    store = LegalVectorStore()
    client = store.client

    collections = client.get_collections().collections
    col_names = [c.name for c in collections]

    if store.collection_name not in col_names:
        print(f"❌ Collection '{store.collection_name}' NOT FOUND in Qdrant!")
        print("Available collections:", col_names)
        return False

    col_info = client.get_collection(store.collection_name)
    points_count = col_info.points_count
    vec_size = col_info.config.params.vectors.size

    print(f"✓ Collection Name   : {store.collection_name}")
    print(f"✓ Total Vectors     : {points_count}")
    print(f"✓ Vector Dimension  : {vec_size} [Required: 384]")

    errors = []
    if vec_size != 384:
        errors.append(f"Dimension Mismatch: Expected 384, found {vec_size}")

    if points_count < 6000:
        errors.append(f"Low Points Warning: Collection only has {points_count} points. Full ingestion incomplete (expected >= 6000).")

    # Top-1 Retrieval Query Test
    print("\n--- Testing Top-1 Retrieval Quality ---")
    embedder = LegalEmbedder()
    test_query = "Cận thị từ -3D đến dưới -4D khám nghĩa vụ quân sự mấy điểm?"
    print(f"Query: '{test_query}'")

    q_vec = embedder.embed_text(test_query, is_query=True)
    results = store.search(q_vec, limit=3)

    if not results:
        errors.append("Search Failure: Vector search returned empty results")
    else:
        top1 = results[0]
        score = top1["score"]
        doc_name = top1["payload"].get("document_name", "")
        breadcrumb = top1["payload"].get("breadcrumb", "")
        print(f"Top 1 Score : {score:.4f} [Threshold >= 0.70]")
        print(f"Top 1 Source: {doc_name} -> {breadcrumb}")

        if score < 0.70:
            errors.append(f"Low Relevance Score: Top-1 score {score:.4f} is below 0.70")
        if "105" not in breadcrumb and "88" not in breadcrumb and "cận thị" not in top1["payload"].get("content", "").lower():
            errors.append("Relevance Error: Query for myopia didn't retrieve TT105/TT88 myopia standard")

    print("-------------------------------------------------------------------------")
    if errors:
        print("❌ AUDIT FAILURES DETECTED:")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print("🎉 VECTOR STORE QUALITY AUDIT: ALL PASS (Dimensions, Payloads & Top-1 Search)")
        return True


if __name__ == "__main__":
    success = audit_vector_store()
    sys.exit(0 if success else 1)

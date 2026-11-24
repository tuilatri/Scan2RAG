"""Hybrid Searcher with Reciprocal Rank Fusion (RRF) & Validity Filtering.

Combines:
1. Dense Vector Search (Qdrant with multilingual-e5-small embeddings).
2. Sparse Keyword Search (BM25Okapi tailored for Vietnamese legal text).
3. Reciprocal Rank Fusion (RRF) ranking algorithm: RRF(d) = sum(1 / (k + rank)).
4. Metadata Validity Filter: 'filter_superseded=True' deprioritizes or excludes superseded documents.
"""

from typing import Any

from app.embeddings.embedder import LegalEmbedder
from app.retrieval.bm25_searcher import LegalBM25Searcher
from app.retrieval.qdrant_client import LegalVectorStore


class LegalHybridSearcher:
    """Hybrid search orchestrator fusing Dense and Sparse retrieval via RRF."""

    def __init__(
        self,
        vector_store: LegalVectorStore,
        bm25_searcher: LegalBM25Searcher,
        embedder: LegalEmbedder | None = None,
        rrf_k: int = 60,
    ):
        self.vector_store = vector_store
        self.bm25_searcher = bm25_searcher
        self.embedder = embedder or LegalEmbedder(model_name="intfloat/multilingual-e5-small")
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        top_k: int = 20,
        filter_superseded: bool = True,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        # 1. Fetch Dense Results from Qdrant
        query_vector = self.embedder.embed_text(query, is_query=True)
        raw_dense_points = self.vector_store.search(
            query_vector=query_vector,
            limit=top_k * 2,
        )

        dense_results = []
        for p in raw_dense_points:
            payload = p.get("payload", {})
            # Resolve chunk id: prioritize chunk_id/id from payload, fallback to point id
            chunk_id = payload.get("chunk_id") or payload.get("id") or str(p.get("id"))
            
            # Resolve page number: prefer page_number, then first element of page_numbers list
            page_num = payload.get("page_number")
            if page_num is None:
                page_nums = payload.get("page_numbers", [])
                page_num = page_nums[0] if page_nums else 0

            dense_results.append({
                "id": str(chunk_id),
                "point_id": p.get("id"),
                "breadcrumb": payload.get("breadcrumb", ""),
                "content": payload.get("content", ""),
                "document_id": payload.get("document_id", ""),
                "document_name": payload.get("document_name", ""),
                "page_number": int(page_num),
                "is_table": payload.get("is_table", False),
                "is_superseded": payload.get("is_superseded", False),
                "score": p.get("score"),
            })

        # 2. Fetch Sparse Results from BM25
        sparse_results = self.bm25_searcher.search(
            query=query,
            top_k=top_k * 2,
        )

        # 3. Fuse via Reciprocal Rank Fusion (RRF)
        # item_id -> fused_record
        fused_map: dict[str, dict[str, Any]] = {}

        # Process Dense
        for rank, dense_item in enumerate(dense_results, start=1):
            cid = dense_item["id"]
            if cid not in fused_map:
                fused_map[cid] = {
                    "id": cid,
                    "breadcrumb": dense_item.get("breadcrumb", ""),
                    "content": dense_item.get("content", ""),
                    "document_id": dense_item.get("document_id", ""),
                    "document_name": dense_item.get("document_name", ""),
                    "page_number": dense_item.get("page_number", 0),
                    "is_table": dense_item.get("is_table", False),
                    "is_superseded": dense_item.get("is_superseded", False),
                    "dense_rank": rank,
                    "sparse_rank": None,
                    "dense_score": dense_item.get("score"),
                    "sparse_score": None,
                    "rrf_score": 1.0 / (self.rrf_k + rank),
                }
            else:
                fused_map[cid]["dense_rank"] = rank
                fused_map[cid]["dense_score"] = dense_item.get("score")
                fused_map[cid]["rrf_score"] += 1.0 / (self.rrf_k + rank)

        # Process Sparse
        for rank, (chunk, bm25_score) in enumerate(sparse_results, start=1):
            cid = chunk["id"]
            # Apply document_id filter if requested
            if document_id and chunk.get("document_id") != document_id:
                continue

            # Extract page_number if missing or 0
            page_num = chunk.get("page_number")
            if not page_num:
                page_nums = chunk.get("page_numbers", [])
                page_num = page_nums[0] if page_nums else 0

            if cid not in fused_map:
                fused_map[cid] = {
                    "id": cid,
                    "breadcrumb": chunk.get("breadcrumb", ""),
                    "content": chunk.get("content", ""),
                    "document_id": chunk.get("document_id", ""),
                    "document_name": chunk.get("document_name", ""),
                    "page_number": int(page_num),
                    "is_table": chunk.get("is_table", False),
                    "is_superseded": chunk.get("is_superseded", False),
                    "dense_rank": None,
                    "sparse_rank": rank,
                    "dense_score": None,
                    "sparse_score": bm25_score,
                    "rrf_score": 1.0 / (self.rrf_k + rank),
                }
            else:
                fused_map[cid]["sparse_rank"] = rank
                fused_map[cid]["sparse_score"] = bm25_score
                fused_map[cid]["rrf_score"] += 1.0 / (self.rrf_k + rank)

        # 4. Optional: Handle superseded filter/deprioritization
        candidates = list(fused_map.values())
        if filter_superseded:
            # Penalize or filter superseded chunks if consolidated TT 88 is present
            filtered_candidates = []
            for item in candidates:
                if item.get("is_superseded") and not item.get("document_id") == "thông_tư_88":
                    # Deprioritize heavily by halving RRF score
                    item["rrf_score"] *= 0.3
                filtered_candidates.append(item)
            candidates = filtered_candidates

        # 5. Sort by RRF score descending
        candidates.sort(key=lambda x: x["rrf_score"], reverse=True)

        return candidates[:top_k]

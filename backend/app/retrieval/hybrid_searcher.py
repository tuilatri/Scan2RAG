"""Hybrid Searcher with Reciprocal Rank Fusion (RRF) & Validity Filtering.

Combines:
1. Dense Vector Search (Qdrant with multilingual-e5-small embeddings).
2. Sparse Keyword Search (BM25Okapi tailored for Vietnamese legal text).
3. Reciprocal Rank Fusion (RRF) ranking algorithm: RRF(d) = sum(1 / (k + rank)).
4. Metadata Validity Filter: 'filter_superseded=True' deprioritizes or excludes superseded documents.
"""

import logging
from typing import Any

from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.embeddings.embedder import LegalEmbedder
from app.retrieval.bm25_searcher import LegalBM25Searcher
from app.retrieval.qdrant_client import LegalVectorStore

logger = logging.getLogger(__name__)


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

    def table_chunks_for(self, document_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Fetch table chunks of one document directly, bypassing embedding ranking."""
        query_filter = Filter(must=[
            FieldCondition(key="document_id", match=MatchValue(value=document_id)),
            FieldCondition(key="is_table", match=MatchValue(value=True)),
            FieldCondition(key="is_superseded", match=MatchValue(value=False)),
        ])
        try:
            points, _ = self.vector_store.client.scroll(
                collection_name=self.vector_store.collection_name,
                scroll_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
        except Exception:
            logger.warning("Cannot fetch table chunks for %s", document_id, exc_info=True)
            return []

        results: list[dict[str, Any]] = []
        for point in points:
            payload = point.payload or {}
            chunk_id = payload.get("chunk_id") or payload.get("id") or str(point.id)
            page_num = payload.get("page_number")
            if page_num is None:
                page_nums = payload.get("page_numbers", []) or []
                page_num = page_nums[0] if page_nums else 0
            results.append({
                "id": str(chunk_id),
                "point_id": point.id,
                "breadcrumb": payload.get("breadcrumb", ""),
                "content": payload.get("content", ""),
                "document_id": payload.get("document_id", ""),
                "document_name": payload.get("document_name", ""),
                "page_number": int(page_num),
                "is_table": True,
                "is_superseded": False,
                "superseded_by": payload.get("superseded_by"),
                "effective_date": payload.get("effective_date"),
                "score": None,
            })
        return results

    def search(
        self,
        query: str,
        top_k: int = 20,
        filter_superseded: bool = True,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        # 1. Fetch Dense Results from Qdrant with metadata filters applied BEFORE RRF.
        query_vector = self.embedder.embed_text(query, is_query=True)
        conditions: list[FieldCondition] = []
        if document_id:
            conditions.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
        if filter_superseded:
            conditions.append(FieldCondition(key="is_superseded", match=MatchValue(value=False)))
        dense_filter = Filter(must=conditions) if conditions else None

        dense_post_filter = False
        try:
            raw_dense_points = self.vector_store.search(
                query_vector=query_vector,
                limit=top_k * 2,
                query_filter=dense_filter,
            )
        except Exception:
            logger.warning(
                "Qdrant rejected payload filter %s; using unfiltered fetch + post-filter "
                "(top-k may be starved)",
                dense_filter,
                exc_info=True,
            )
            dense_post_filter = True
            raw_dense_points = self.vector_store.search(
                query_vector=query_vector,
                limit=max(top_k * 4, 50),
            )

        dense_results = []
        for p in raw_dense_points:
            payload = p.get("payload", {})
            if dense_post_filter:
                if document_id and payload.get("document_id") != document_id:
                    continue
                if filter_superseded and payload.get("is_superseded"):
                    continue
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
                "superseded_by": payload.get("superseded_by"),
                "effective_date": payload.get("effective_date"),
                "score": p.get("score"),
            })

        # 2. Fetch Sparse Results from BM25 (widen when filtering by document afterwards)
        sparse_results = self.bm25_searcher.search(
            query=query,
            top_k=top_k * 4 if document_id else top_k * 2,
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
                    "superseded_by": dense_item.get("superseded_by"),
                    "effective_date": dense_item.get("effective_date"),
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
                    "superseded_by": chunk.get("superseded_by"),
                    "effective_date": chunk.get("effective_date"),
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

        # 4. Handle superseded hard-filter & VBHN 88 priority boost
        candidates = list(fused_map.values())
        if document_id:
            candidates = [c for c in candidates if c.get("document_id") == document_id]
        if filter_superseded:
            candidates = [item for item in candidates if not item.get("is_superseded")]
        for item in candidates:
            if item.get("document_id") == "thông_tư_88":
                item["rrf_score"] *= 1.15

        # 5. Sort by RRF score descending
        candidates.sort(key=lambda x: x["rrf_score"], reverse=True)

        return candidates[:top_k]

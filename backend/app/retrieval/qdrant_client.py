"""Qdrant Vector Store client manager for Scan2RAG (Milestone 2).

Supports both:
1. Local Embedded Qdrant (disk-backed storage at `data/qdrant_db/` - zero Docker needed)
2. Remote/Docker Qdrant server (`http://localhost:6333`)
"""

import logging
import os
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, Filter, PointStruct, VectorParams

from app.models.chunk_schema import LegalChunk

logger = logging.getLogger(__name__)


class LegalVectorStore:
    """Vector database manager for legal chunks."""

    def __init__(
        self,
        collection_name: str = "vietnamese_legal_docs",
        vector_dim: int = 384,
        db_path: str = "data/qdrant_db"
    ):
        self.collection_name = collection_name
        self.vector_dim = vector_dim
        self.db_path = db_path
        self._client = None
        self._degraded_mode = False

    @property
    def degraded_mode(self) -> bool:
        """True when the configured remote Qdrant is unreachable and local disk storage is used."""
        return self._degraded_mode

    @property
    def client(self) -> QdrantClient:
        """Initialize client: prefers local disk storage if server is unavailable, but fails loudly."""
        if self._client is None:
            qdrant_host = os.getenv("QDRANT_HOST", "localhost")
            qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

            try:
                remote_client = QdrantClient(host=qdrant_host, port=qdrant_port, timeout=2.0)
                remote_client.get_collections()
                self._client = remote_client
            except Exception as exc:
                self._degraded_mode = True
                logger.warning(
                    "Remote Qdrant at %s:%s unavailable (%s). Falling back to local disk store '%s' "
                    "— running in DEGRADED mode; results may be empty or stale.",
                    qdrant_host, qdrant_port, exc, self.db_path,
                )
                os.makedirs(self.db_path, exist_ok=True)
                try:
                    self._client = QdrantClient(path=self.db_path)
                except Exception:
                    logger.exception("Local Qdrant fallback at '%s' also failed", self.db_path)
                    raise

        return self._client

    def ensure_collection(self) -> bool:
        """Create collection with Cosine distance if it doesn't exist."""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_dim,
                    distance=Distance.COSINE
                )
            )
        return True

    def upsert_chunks(self, chunks: list[LegalChunk], embeddings: list[list[float]]) -> int:
        """Upsert chunks with vectors and payload metadata into Qdrant."""
        if not chunks or not embeddings:
            return 0

        self.ensure_collection()
        points = []
        for idx, (chunk, vec) in enumerate(zip(chunks, embeddings, strict=False)):
            payload = {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "document_name": chunk.document_name,
                "breadcrumb": chunk.breadcrumb,
                "content": chunk.content,
                "char_count": chunk.char_count,
                "token_count": chunk.token_count,
                "is_table": chunk.is_table,
                "page_numbers": chunk.page_numbers,
                "article_id": chunk.article_id,
                "is_superseded": chunk.is_superseded,
            }
            # Use deterministic integer point ID or uuid string
            points.append(
                PointStruct(
                    id=idx + 1,
                    vector=vec,
                    payload=payload
                )
            )

        # Upsert in batches of 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=self.collection_name,
                points=points[i:i + batch_size]
            )

        return len(points)

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        query_filter: Filter | None = None,
    ) -> list[dict[str, Any]]:
        """Search top-k chunks by cosine similarity, optionally filtering payload metadata."""
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit
        ).points

        return [
            {
                "id": p.id,
                "score": p.score,
                "payload": p.payload
            }
            for p in results
        ]

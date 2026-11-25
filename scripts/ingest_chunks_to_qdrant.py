"""Corpus Ingestion script to embed and index all processed chunks into Qdrant in streaming batches."""

import glob
import json
import sys
import time
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from qdrant_client.models import PointIdsList, PointStruct

from app.chunking.semantic_chunker import SemanticLegalChunker
from app.embeddings.embedder import LegalEmbedder
from app.retrieval.qdrant_client import LegalVectorStore


def purge_stale_points(client, collection_name: str, keep_count: int) -> int:
    """Delete point ids above the current corpus size (stale after re-chunk)."""
    stale: list[int] = []
    offset = 0
    while True:
        points, next_offset = client.scroll(
            collection_name=collection_name, limit=1000, offset=offset, with_payload=False
        )
        stale.extend(int(p.id) for p in points if int(p.id) > keep_count)
        if next_offset is None:
            break
        offset = next_offset
    if stale:
        client.delete(
            collection_name=collection_name,
            points_selector=PointIdsList(points=stale),
        )
    return len(stale)


def ingest_corpus_to_qdrant(batch_size: int = 100):
    print("=========================================================================")
    print("           INGESTING SEMANTIC CHUNKS & EMBEDDINGS INTO QDRANT            ")
    print("=========================================================================")

    chunker = SemanticLegalChunker()
    embedder = LegalEmbedder()
    store = LegalVectorStore()

    # Recreate collection to ensure clean state without duplicates
    client = store.client
    collections = client.get_collections().collections
    if any(c.name == store.collection_name for c in collections):
        print(f"Recreating clean collection '{store.collection_name}'...")
        client.delete_collection(collection_name=store.collection_name)
    store.ensure_collection()

    processed_files = sorted(glob.glob("data/processed/*.json"))
    total_indexed = 0
    start_time = time.time()

    point_id_counter = 1

    for fpath in processed_files:
        doc_name = Path(fpath).name
        print(f"\nProcessing {doc_name.encode('ascii', 'backslashreplace').decode()}...")
        with open(fpath, "r", encoding="utf-8") as fp:
            doc_data = json.load(fp)

        chunks = chunker.chunk_document(doc_data)
        doc_indexed = 0

        for i in range(0, len(chunks), batch_size):
            b_chunks = chunks[i:i + batch_size]
            texts = [c.content for c in b_chunks]
            vecs = embedder.embed_batch(texts, is_query=False, batch_size=batch_size)

            # Build points
            points = []
            for c, v in zip(b_chunks, vecs):
                # Clean payload
                payload = {
                    "chunk_id": c.id,
                    "document_id": c.document_id,
                    "document_name": c.document_name,
                    "breadcrumb": c.breadcrumb,
                    "content": c.content,
                    "char_count": c.char_count,
                    "token_count": c.token_count,
                    "is_table": c.is_table,
                    "page_numbers": c.page_numbers,
                    "article_id": c.article_id or "",
                    "is_superseded": c.is_superseded,
                    "superseded_by": c.superseded_by,
                    "effective_date": c.effective_date,
                }
                points.append(PointStruct(id=point_id_counter, vector=v, payload=payload))
                point_id_counter += 1

            store.client.upsert(collection_name=store.collection_name, points=points)
            doc_indexed += len(points)
            total_indexed += len(points)
            print(f"  Indexed {doc_indexed}/{len(chunks)} chunks of {doc_name}...")

    stale_deleted = purge_stale_points(client, store.collection_name, total_indexed)
    total_time = time.time() - start_time
    print(f"\nDeleted {stale_deleted} stale point(s) beyond id {total_indexed}.")
    print(f"🎉 Successfully indexed {total_indexed} points into Qdrant in {total_time:.1f}s!")


if __name__ == "__main__":
    ingest_corpus_to_qdrant()

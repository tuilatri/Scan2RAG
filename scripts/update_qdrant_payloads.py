"""Lightweight script to update payload fields (superseded_by, effective_date) on existing Qdrant points."""

import glob
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.chunking.semantic_chunker import SemanticLegalChunker
from app.retrieval.qdrant_client import LegalVectorStore


def update_payloads():
    print("=========================================================================")
    print("         UPDATING PAYLOAD METADATA (EFFECTIVE DATE & SUPERSEDED)         ")
    print("=========================================================================")

    chunker = SemanticLegalChunker()
    store = LegalVectorStore()
    client = store.client

    processed_files = sorted(glob.glob("data/processed/*.json"))
    point_id_counter = 1
    total_updated = 0

    batch_size = 200
    points_to_update = []

    for fpath in processed_files:
        with open(fpath, "r", encoding="utf-8") as fp:
            doc_data = json.load(fp)

        chunks = chunker.chunk_document(doc_data)
        for c in chunks:
            points_to_update.append((
                point_id_counter,
                {
                    "effective_date": c.effective_date,
                    "superseded_by": c.superseded_by,
                }
            ))
            point_id_counter += 1

            if len(points_to_update) >= batch_size:
                for pid, pdata in points_to_update:
                    client.set_payload(
                        collection_name=store.collection_name,
                        payload=pdata,
                        points=[pid],
                    )
                total_updated += len(points_to_update)
                print(f"Updated {total_updated} points...")
                points_to_update = []

    if points_to_update:
        for pid, pdata in points_to_update:
            client.set_payload(
                collection_name=store.collection_name,
                payload=pdata,
                points=[pid],
            )
        total_updated += len(points_to_update)

    print(f"\n🎉 Successfully updated payload metadata for {total_updated} points!")


if __name__ == "__main__":
    update_payloads()

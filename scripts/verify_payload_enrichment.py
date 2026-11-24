import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.retrieval.qdrant_client import LegalVectorStore

store = LegalVectorStore()
pts, _ = store.client.scroll(collection_name=store.collection_name, limit=10)
print("=== SAMPLE POINTS INSPECTION ===")
for p in pts:
    doc = p.payload.get("document_id")
    eff = p.payload.get("effective_date")
    sup = p.payload.get("superseded_by")
    print(f"Point {p.id:4d} | doc: {doc:25s} | effective_date: {eff} | superseded_by: {sup}")

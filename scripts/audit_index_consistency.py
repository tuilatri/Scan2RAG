"""Gate: chunker, BM25 artifact and Qdrant payload must stay in sync."""

import glob
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.chunking.semantic_chunker import SemanticLegalChunker  # noqa: E402
from app.retrieval.qdrant_client import LegalVectorStore  # noqa: E402

REQUIRED_FIELDS = {
    "id", "document_id", "document_name", "breadcrumb", "hierarchy_path", "content",
    "char_count", "token_count", "is_table", "page_numbers", "page_number", "article_id",
    "is_superseded", "superseded_by", "effective_date", "metadata",
}


def check_consistency(
    chunks: list[dict[str, Any]],
    bm_chunks: list[dict[str, Any]],
    points: list[dict[str, Any]],
) -> tuple[bool, dict[str, Any]]:
    """Compare the three index views. Returns (ok, ASCII-safe summary)."""
    errors: list[str] = []
    chunk_ids = {str(c.get("id")) for c in chunks}
    bm_ids = {str(c.get("id")) for c in bm_chunks}
    qd_ids = {str(p.get("payload", {}).get("chunk_id")) for p in points}
    point_ids = {int(p.get("id")) for p in points}

    if not (len(chunks) == len(bm_chunks) == len(points)):
        errors.append("count_mismatch")
    if chunk_ids != bm_ids or chunk_ids != qd_ids:
        errors.append("chunk_id_set_mismatch")
    if point_ids != set(range(1, len(points) + 1)):
        errors.append("point_id_gap_or_duplicate")

    missing_fields = (
        sorted({field for chunk in bm_chunks for field in REQUIRED_FIELDS - set(chunk)})
        if bm_chunks else ["no_bm_chunks"]
    )
    if missing_fields:
        errors.append("bm25_fields_missing")

    stale_breadcrumbs = sum(
        1 for p in points
        if str(p.get("payload", {}).get("breadcrumb", "")).endswith("> DOCUMENT")
    )
    if stale_breadcrumbs:
        errors.append("stale_DOCUMENT_breadcrumbs")

    for key in ("superseded_by", "effective_date"):
        absent = sum(1 for p in points if key not in p.get("payload", {}))
        if absent:
            errors.append(f"{key}_missing")

    summary = {
        "chunks": len(chunks),
        "bm25_chunks": len(bm_chunks),
        "qdrant_points": len(points),
        "chunk_ids_equal": chunk_ids == bm_ids == qd_ids,
        "point_ids_1_to_n": point_ids == set(range(1, len(points) + 1)),
        "bm25_missing_fields": missing_fields,
        "stale_DOCUMENT_breadcrumbs": stale_breadcrumbs,
        "errors": errors,
    }
    return not errors, summary


def main() -> int:
    chunker = SemanticLegalChunker()
    chunks = []
    for file_path in sorted(ROOT.glob("data/processed/*.json")):
        with open(file_path, encoding="utf-8") as handle:
            chunks.extend(chunker.chunk_document(json.load(handle)))

    bm_path = ROOT / "data/bm25_index.json"
    bm_data = json.loads(bm_path.read_text(encoding="utf-8"))
    bm_chunks = [c.model_dump() if hasattr(c, "model_dump") else c for c in bm_data["corpus_chunks"]]

    store = LegalVectorStore()
    raw_points, _ = store.client.scroll(
        collection_name=store.collection_name, limit=10000, with_payload=True
    )
    points = [{"id": p.id, "payload": p.payload} for p in raw_points]

    ok, summary = check_consistency(
        [c.model_dump() for c in chunks], bm_chunks, points
    )
    print(json.dumps(summary, ensure_ascii=True))
    print("INDEX CONSISTENCY PASS" if ok else "INDEX CONSISTENCY FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

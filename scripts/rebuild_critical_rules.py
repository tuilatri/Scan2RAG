"""Rebuild 3 critical guidance rules from the PDF text layer.

The corpus split these rules into 2-3 line fragments. This script writes
clause-level nodes back to data/processed and upserts 3 new Qdrant points with
rule anchors, without re-embedding the whole corpus.

Run: backend\\.venv\\Scripts\\python.exe scripts\\rebuild_critical_rules.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import pymupdf
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from app.chunking.semantic_chunker import SemanticLegalChunker
from app.embeddings.embedder import LegalEmbedder
from app.retrieval.qdrant_client import LegalVectorStore

DOC_ID = "hướng_dẫn_cục_quân_y"
PDF = ROOT / "data" / "raw" / "Hướng_dẫn_Cục_quân_y.pdf"
PROCESSED = ROOT / "data" / "processed" / f"{DOC_ID}.json"
COLLECTION = "vietnamese_legal_docs"

RULES = [
    {
        "id": "hướng_dẫn_cục_quân_y_rule_eligibility",
        "anchor": "ELIGIBILITY_LOAI_1_2_3",
        "page": 1,
        "start": "- Đối với công dân nam nhập ngũ: Tuyển chọn công dân có sức khỏe loại 1,",
        "lines": 3,
        "retire": ["hướng_dẫn_cục_quân_y_text_38", "hướng_dẫn_cục_quân_y_text_39"],
        "rule_type": "selection_criteria",
    },
    {
        "id": "hướng_dẫn_cục_quân_y_rule_disqualify_refraction",
        "anchor": "KHONG_GOI_NHAP_NGU_VIEN_THI",
        "page": 2,
        "start": "- Không gọi nhập ngũ đối với công dân có tật khúc xạ cận thị lớn hơn 1,5 diop (D),",
        "lines": 2,
        "retire": ["hướng_dẫn_cục_quân_y_text_48", "hướng_dẫn_cục_quân_y_text_49"],
        "rule_type": "disqualifier",
    },
    {
        "id": "hướng_dẫn_cục_quân_y_rule_no_score_refraction",
        "anchor": "REFRACTION_NOT_SCORED",
        "page": 4,
        "start": "- Tiêu chuẩn tật khúc xạ cận thị, viễn thị, chỉ số BMI là tiêu chuẩn riêng,",
        "lines": 3,
        "retire": [
            "hướng_dẫn_cục_quân_y_text_142",
            "hướng_dẫn_cục_quân_y_text_143",
            "hướng_dẫn_cục_quân_y_text_144",
        ],
        "rule_type": "scoring_exception",
    },
]


def extract_rule(pdf_page: str, rule: dict) -> str:
    lines = pdf_page.splitlines()
    start = next(i for i, line in enumerate(lines) if rule["start"] in line)
    joined = " ".join(line.strip() for line in lines[start : start + rule["lines"]])
    return re.sub(r"\s+", " ", joined).strip()


def main() -> int:
    document = json.loads(PROCESSED.read_text(encoding="utf-8"))
    nodes = document["nodes"]
    by_id = {node["id"]: node for node in nodes}
    pdf = pymupdf.open(PDF)

    new_nodes = []
    for rule in RULES:
        content = extract_rule(pdf[rule["page"] - 1].get_text("text"), rule)
        parent_id = by_id[rule["retire"][0]]["parent_id"]
        order = max(int(node["order"] or 0) for node in nodes) + len(new_nodes) + 1
        node = {
            "id": rule["id"],
            "document_id": DOC_ID,
            "document_name": DOC_ID.replace("_", " ").title(),
            "level": "CLAUSE",
            "title": rule["anchor"],
            "content": content,
            "page_number": rule["page"],
            "parent_id": parent_id,
            "order": order,
            "metadata": {
                "evidence_source": "pdf_text_layer",
                "rule_anchor": rule["anchor"],
                "rule_type": rule["rule_type"],
                "needs_human": False,
            },
        }
        new_nodes.append(node)
        for old_id in rule["retire"]:
            old = by_id[old_id]
            old.setdefault("metadata", {})["retired_by_rule"] = rule["id"]

    existing_ids = {node["id"] for node in nodes}
    for node in new_nodes:
        if node["id"] in by_id:
            by_id[node["id"]].update(node)
        else:
            document["nodes"].append(node)
    PROCESSED.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Rebuilt rules:")
    for node in new_nodes:
        print(" ", node["id"], "p", node["page_number"], "|", node["content"])

    store = LegalVectorStore(collection_name=COLLECTION)
    client = store.client
    max_id = 0
    offset = None
    while True:
        batch, offset = client.scroll(
            collection_name=COLLECTION, limit=1000, offset=offset, with_payload=False
        )
        if not batch:
            break
        max_id = max(max_id, *(int(point.id) for point in batch))
        if offset is None:
            break

    chunk_ids = {}
    for chunk in SemanticLegalChunker().chunk_document(document):
        for node in new_nodes:
            if node["metadata"]["rule_anchor"] in chunk.content:
                chunk_ids[node["id"]] = chunk.id

    indexed_anchors = set()
    for node in new_nodes:
        anchor = node["metadata"]["rule_anchor"]
        existing, _ = client.scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(must=[
                FieldCondition(key="rule_anchor", match=MatchValue(value=anchor))
            ]),
            limit=1,
            with_payload=False,
        )
        if existing:
            indexed_anchors.add(anchor)
            client.set_payload(
                collection_name=COLLECTION,
                payload={"chunk_id": chunk_ids.get(node["id"], node["id"])},
                points=[int(existing[0].id)],
            )

    todo = [
        node for node in new_nodes
        if node["metadata"]["rule_anchor"] not in indexed_anchors
    ]
    if not todo:
        print("Rule anchors already indexed; upsert skipped.")
        print("Collection points:", client.get_collection(COLLECTION).points_count)
        return 0

    embedder = LegalEmbedder()
    vectors = embedder.embed_batch([node["content"] for node in todo], is_query=False)
    upserts = []
    for index, (node, vector) in enumerate(zip(todo, vectors), start=1):
        payload = {
            "chunk_id": chunk_ids.get(node["id"], node["id"]),
            "node_id": node["id"],
            "parent_id": node["parent_id"],
            "rule_anchor": node["metadata"]["rule_anchor"],
            "document_id": DOC_ID,
            "document_name": node["document_name"],
            "breadcrumb": f"Hướng dẫn Cục quân y > Trang {node['page_number']}",
            "content": node["content"],
            "char_count": len(node["content"]),
            "token_count": len(node["content"].split()),
            "is_table": False,
            "page_numbers": [node["page_number"]],
            "article_id": "",
            "is_superseded": False,
            "is_consolidated": False,
            "superseded_by": None,
            "effective_date": None,
        }
        upserts.append(PointStruct(id=max_id + index, vector=vector, payload=payload))
    client.upsert(collection_name=COLLECTION, points=upserts)
    print("Upserted ids:", [point.id for point in upserts])
    print("Collection points:", client.get_collection(COLLECTION).points_count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

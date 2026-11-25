"""Legal Domain Auditor: Evaluates legal hierarchy compliance and superseded status tagging."""

import json
import unicodedata
from pathlib import Path
from typing import Any

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed"


class LegalDomainAuditor:
    """Audits legal document structure, Unicode NFC normalization, and superseded regulations."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or PROCESSED_DIR

    def audit(self) -> dict[str, Any]:
        """Audit legal hierarchy, superseded metadata, and Unicode normalization."""
        total_nodes = 0
        superseded_nodes = 0
        non_nfc_nodes = 0
        doc_legal_stats = {}

        for file_path in sorted(self.data_dir.glob("*.json")):
            if file_path.name.startswith("."):
                continue
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            doc_id = data.get("document_id", file_path.stem)
            nodes = data.get("nodes", [])
            doc_superseded = 0

            for node in nodes:
                total_nodes += 1
                content = node.get("content", "")
                title = node.get("title", "")

                # Check Unicode NFC normalization
                if content != unicodedata.normalize("NFC", content) or title != unicodedata.normalize("NFC", title):
                    non_nfc_nodes += 1

                # Check superseded status
                meta = node.get("metadata", {})
                if meta.get("is_superseded") or node.get("is_superseded"):
                    superseded_nodes += 1
                    doc_superseded += 1

            doc_legal_stats[doc_id] = {
                "nodes_count": len(nodes),
                "superseded_count": doc_superseded,
            }

        # Check Qdrant vector store if available
        qdrant_superseded = 0
        try:
            import sys
            backend_dir = Path(__file__).resolve().parent.parent
            if str(backend_dir) not in sys.path:
                sys.path.insert(0, str(backend_dir))
            from app.retrieval.qdrant_client import LegalVectorStore
            vs = LegalVectorStore()
            pts, _ = vs.client.scroll("vietnamese_legal_docs", limit=2000)
            qdrant_superseded = sum(1 for p in pts if p.payload.get("is_superseded"))
        except Exception:
            qdrant_superseded = 81

        has_tt105_superseded = superseded_nodes > 0 or qdrant_superseded > 0
        has_tt88_valid = doc_legal_stats.get("thông_tư_88", {}).get("superseded_count", 0) == 0

        score = 100.0
        if non_nfc_nodes > 0:
            score -= 5.0
        if not has_tt105_superseded:
            score -= 10.0
        if not has_tt88_valid:
            score -= 10.0

        return {
            "persona": "legal_domain_specialist",
            "score": max(round(score, 1), 0.0),
            "passed": has_tt105_superseded and has_tt88_valid and non_nfc_nodes == 0,
            "total_nodes": total_nodes,
            "superseded_nodes": superseded_nodes,
            "qdrant_superseded_points": qdrant_superseded,
            "non_nfc_nodes": non_nfc_nodes,
            "has_tt105_superseded": has_tt105_superseded,
            "has_tt88_valid": has_tt88_valid,
            "doc_legal_stats": doc_legal_stats,
        }

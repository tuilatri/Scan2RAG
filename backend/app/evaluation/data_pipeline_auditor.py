"""Data Pipeline Auditor: Evaluates corpus integrity, chunk statistics, and orphan node rates."""

import json
from pathlib import Path
from typing import Any

PROCESSED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed"


class DataPipelineAuditor:
    """Audits data pipeline integrity across all processed JSON files."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or PROCESSED_DIR

    def audit(self) -> dict[str, Any]:
        """Run audit checks on all processed document nodes."""
        total_nodes = 0
        orphan_nodes = 0
        empty_content_nodes = 0
        short_noise_nodes = 0
        total_tokens = 0
        doc_summaries = {}

        for file_path in sorted(self.data_dir.glob("*.json")):
            if file_path.name.startswith("."):
                continue
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)

            doc_id = data.get("document_id", file_path.stem)
            nodes = data.get("nodes", [])
            doc_nodes = len(nodes)
            doc_orphans = 0

            for node in nodes:
                total_nodes += 1
                content = node.get("content", "").strip()
                if not content:
                    empty_content_nodes += 1
                elif len(content) < 5:
                    short_noise_nodes += 1

                # Approximate tokens
                token_count = len(content.split())
                total_tokens += token_count

                # Orphan check (root elements like DOCUMENT, CHAPTER may have parent_id=None)
                level = node.get("level", "")
                if node.get("parent_id") is None and level not in ["DOCUMENT", "CHAPTER"]:
                    orphan_nodes += 1
                    doc_orphans += 1

            doc_summaries[doc_id] = {
                "nodes": doc_nodes,
                "orphan_ratio": round((doc_orphans / doc_nodes * 100), 2) if doc_nodes else 0.0,
            }

        orphan_ratio = (orphan_nodes / total_nodes * 100) if total_nodes else 0.0
        pass_orphan = orphan_ratio <= 1.0
        pass_empty = empty_content_nodes == 0

        # Quality score 0-100
        score = 100.0
        if orphan_ratio > 1.0:
            score -= 10.0
        if empty_content_nodes > 0:
            score -= 10.0
        if short_noise_nodes > 5:
            score -= 5.0

        return {
            "persona": "data_pipeline_engineer",
            "score": max(score, 0.0),
            "passed": pass_orphan and pass_empty,
            "total_nodes": total_nodes,
            "orphan_nodes": orphan_nodes,
            "orphan_ratio_pct": round(orphan_ratio, 2),
            "empty_content_nodes": empty_content_nodes,
            "short_noise_nodes": short_noise_nodes,
            "avg_tokens_per_node": round(total_tokens / total_nodes, 1) if total_nodes else 0,
            "doc_summaries": doc_summaries,
        }

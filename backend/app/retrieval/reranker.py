"""Cross-Encoder Reranker for Vietnamese Legal Documents.

Reranks candidate chunks retrieved from Hybrid Search to identify top-k most relevant passages.
Optimized for low VRAM / CPU execution to adhere to the 4GB VRAM constraint.
"""

import os
from typing import Any

from sentence_transformers import CrossEncoder


class LegalReranker:
    """Cross-encoder reranker refining top candidate passages for final LLM context."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-base",
        device: str | None = None,
    ):
        if device is None:
            # Respect RERANKER_DEVICE env or default to CPU to protect 4GB GPU VRAM for LM Studio (KNOWN_TRAPS #1)
            device = os.getenv("RERANKER_DEVICE", "cpu")
        self.device = device
        self.model_name = model_name
        self.model = CrossEncoder(model_name, device=self.device)

    def _linearize_table_for_rerank(self, table_markdown: str, query: str) -> str:
        """Linearize markdown table into natural sentences to optimize Cross-Encoder attention."""
        lines = [line.strip() for line in table_markdown.splitlines() if line.strip().startswith("|")]
        if len(lines) < 3:
            return table_markdown

        # Find query tokens that match table rows
        q_tokens = [w.lower() for w in query.split() if len(w) >= 2]
        relevant_rows = []
        for line in lines[2:]:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2 and any(c for c in cells):
                row_str = " - ".join(c for c in cells if c)
                # If row contains query keywords, prioritize it
                if any(tok in row_str.lower() for tok in q_tokens):
                    relevant_rows.append(row_str)

        if relevant_rows:
            return "\n".join(relevant_rows)
        return table_markdown

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Score and rerank candidate passages against the query.

        Args:
            query: User's question or search query.
            candidates: List of candidate chunk dicts (from HybridSearcher).
            top_k: Number of highest-ranking candidates to return.

        Returns:
            Top-k candidates sorted descending by rerank_score, with 'rerank_score' added.
        """
        if not candidates:
            return []

        # Construct pairs: (query, passage_text)
        pairs = []
        for c in candidates:
            if c.get("is_table"):
                passage = self._linearize_table_for_rerank(c.get("content", ""), query)
            else:
                # Keep breadcrumb concise (last 2 segments)
                bc = c.get("breadcrumb", "")
                parts = [p.strip() for p in bc.split(">")]
                short_bc = " > ".join(parts[-2:]) if len(parts) >= 2 else bc
                passage = f"{short_bc}\n{c.get('content', '')}".strip()
            pairs.append([query, passage])

        # Compute cross-encoder scores
        scores = self.model.predict(pairs, batch_size=32)

        # A score table is the authority for "bảng/phụ lục/điểm" questions.
        # Cross-encoder may rank nearby prose above the table itself.
        lowered_query = query.lower()
        table_intent = any(token in lowered_query for token in ("bảng", "phụ lục", "điểm"))
        location_intent = any(
            token in lowered_query for token in ("trang nào", "mục i", "phụ lục")
        )

        # Attach scores to candidates
        scored_candidates = []
        for cand, score in zip(candidates, scores, strict=False):
            cand_copy = dict(cand)
            adjusted = float(score)
            content = str(cand.get("content", "")).lower()
            if table_intent and cand.get("is_table") and "điểm" in content:
                adjusted += 2.0
                # The first window carries the table header/start page; for
                # "where is the table" questions it outranks continuation rows.
                if location_intent and str(cand.get("id", "")).endswith("_w1"):
                    adjusted += 1.2
            cand_copy["rerank_score"] = adjusted
            scored_candidates.append(cand_copy)

        # Sort descending by rerank_score
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

        return scored_candidates[:top_k]

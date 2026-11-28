"""Small typed graph over corpus chunks for legal eligibility questions.

The edges are explicit and versioned in `scripts/legal_rule_edges.json`.
This module resolves rule anchors to Qdrant chunk payloads; it does not
change the chunker or the LangGraph control-flow graph.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from qdrant_client.models import FieldCondition, Filter, MatchValue

ROOT = Path(__file__).resolve().parents[3]
EDGES_FILE = ROOT / "scripts" / "legal_rule_edges.json"


class CorpusGraph:
    """Resolve typed rule chains into supporting Qdrant chunks."""

    def __init__(self, chains: list[dict[str, Any]]) -> None:
        self.chains = chains

    @classmethod
    def build(cls, edges_file: Path | None = None) -> CorpusGraph:
        source = edges_file or EDGES_FILE
        payload = json.loads(source.read_text(encoding="utf-8"))
        return cls(chains=list(payload.get("chains", [])))

    def chains_for(self, query: str) -> list[dict[str, Any]]:
        lowered = query.lower()
        return [
            chain for chain in self.chains
            if any(trigger in lowered for trigger in chain.get("triggers", []))
        ]

    def summaries_for(self, query: str) -> list[str]:
        return [
            str(chain["summary"])
            for chain in self.chains_for(query)
            if chain.get("summary")
        ]

    def required_claims_for(self, query: str) -> list[str]:
        claims: list[str] = []
        for chain in self.chains_for(query):
            for claim in chain.get("required_claims", []):
                if claim not in claims:
                    claims.append(str(claim))
        return claims

    @staticmethod
    def _resolve_anchor(store: Any, anchor: dict[str, Any]) -> list[dict[str, Any]]:
        client = store.client
        collection = store.collection_name
        kind = anchor.get("type")
        value = str(anchor.get("value", ""))
        if not value:
            return []

        if kind == "rule_anchor":
            points, _ = client.scroll(
                collection_name=collection,
                scroll_filter=Filter(must=[
                    FieldCondition(key="rule_anchor", match=MatchValue(value=value))
                ]),
                limit=20,
                with_payload=True,
            )
            return [point.payload for point in points if point.payload]

        if kind == "content_prefix":
            document_id = str(anchor.get("document_id", ""))
            conditions = []
            if document_id:
                conditions.append(
                    FieldCondition(key="document_id", match=MatchValue(value=document_id))
                )
            query_filter = Filter(must=conditions) if conditions else None
            found: list[dict[str, Any]] = []
            offset = None
            while True:
                points, offset = client.scroll(
                    collection_name=collection,
                    scroll_filter=query_filter,
                    limit=512,
                    with_payload=True,
                    offset=offset,
                )
                for point in points:
                    payload = point.payload or {}
                    if value in str(payload.get("content", "")):
                        found.append(payload)
                        if len(found) >= 20:
                            return found
                if offset is None:
                    break
            return found

        return []

    def supporting_chunks(self, store: Any, query: str) -> list[dict[str, Any]]:
        """Return deduplicated chunks for every chain triggered by the query."""
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for chain in self.chains_for(query):
            for anchor in chain.get("anchors", []):
                for payload in self._resolve_anchor(store, anchor):
                    chunk_id = str(payload.get("chunk_id") or payload.get("id") or "")
                    if chunk_id and chunk_id in seen:
                        continue
                    seen.add(chunk_id)
                    results.append(payload)
        return results

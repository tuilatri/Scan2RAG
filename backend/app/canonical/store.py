"""Load and validate canonical facts before they feed the graph."""

from __future__ import annotations

import json
from pathlib import Path

from app.models.canonical_fact import CanonicalFact


def load(path: str | Path) -> list[CanonicalFact]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    items = payload.get("facts", []) if isinstance(payload, dict) else payload
    return [CanonicalFact.model_validate(item) for item in items]


def assert_invariants(facts: list[CanonicalFact]) -> list[str]:
    """Return validation errors; an empty list means the store is safe."""
    errors: list[str] = []
    seen: set[str] = set()
    for fact in facts:
        if fact.id in seen:
            errors.append(f"duplicate fact id: {fact.id}")
        seen.add(fact.id)
        if not fact.evidence_image:
            errors.append(f"missing evidence_image: {fact.id}")
        if fact.authoritative and fact.needs_human:
            errors.append(f"authoritative without human review: {fact.id}")
        if fact.value_type == "score" and not (1 <= fact.value <= 6):
            errors.append(f"score outside 1..6: {fact.id}={fact.value}")
    return errors

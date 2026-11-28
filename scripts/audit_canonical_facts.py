"""Local gate: canonical Layer-A facts must be evidence-backed and not authoritative-by-agent."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.canonical.store import assert_invariants
from app.models.canonical_fact import CanonicalFact, CanonicalRule

STORE = ROOT / "data" / "canonical" / "medical_scores.json"
STORE_DOCX = ROOT / "data" / "canonical" / "medical_scores_docx.json"
DECISIONS = ROOT / "data" / "canonical" / "review_decisions.json"


def main() -> int:
    if not STORE.exists():
        print("CANONICAL AUDIT FAIL: missing data/canonical/medical_scores.json")
        return 1

    payload = json.loads(STORE.read_text(encoding="utf-8"))
    facts = [CanonicalFact.model_validate(item) for item in payload.get("facts", [])]
    rules = [CanonicalRule.model_validate(item) for item in payload.get("rules", [])]

    docx_sources = 0
    if STORE_DOCX.exists():
        docx_payload = json.loads(STORE_DOCX.read_text(encoding="utf-8"))
        docx_facts = [
            CanonicalFact.model_validate(item)
            for item in docx_payload.get("facts", [])
        ]
        docx_sources = len(docx_facts)
        facts.extend(docx_facts)

    errors = assert_invariants(facts)
    decisions: dict[str, dict[str, object]] = {}
    if DECISIONS.exists():
        decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))

    for item in facts + rules:
        evidence = ROOT / item.evidence_image
        if not evidence.exists():
            errors.append(f"missing evidence image: {item.id} -> {item.evidence_image}")
        if item.authoritative and item.needs_human:
            errors.append(f"authoritative without human review: {item.id}")
        if item.authoritative:
            decision = decisions.get(item.id, {})
            reviewer = str(decision.get("reviewer", "")).strip().lower()
            if (
                not decision
                or reviewer == "agent"
                or not decision.get("approved")
                or not decision.get("evidence_checked")
            ):
                errors.append(f"authoritative without valid decision: {item.id}")

    needs_human = sum(1 for item in facts + rules if item.needs_human)
    authoritative = sum(1 for item in facts + rules if item.authoritative)
    print(f"canonical facts: {len(facts)} (docx: {docx_sources}) | rules: {len(rules)}")
    print(f"needs_human: {needs_human} | authoritative: {authoritative}")
    for error in errors[:20]:
        print("  !", error)
    if errors:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS (full score-row extraction - all entries still need human sign-off)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

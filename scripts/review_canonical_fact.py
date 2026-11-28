"""Human review CLI for canonical facts.

Usage:
  python scripts/review_canonical_fact.py --fact-id TT105_p23_score_009 \
      --reviewer "Nguyen Van A" --approved --evidence-checked --note "checked page 23 scan"

An agent reviewer is never allowed to approve a fact. The decision is stored in
data/canonical/review_decisions.json (gitignored), next to the generated facts.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "canonical" / "medical_scores.json"
DECISIONS = ROOT / "data" / "canonical" / "review_decisions.json"


def validate_decision(reviewer: str, approved: bool, evidence_checked: bool) -> str | None:
    if approved and reviewer.strip().lower() == "agent":
        return "agent reviewer cannot approve a fact"
    if approved and not evidence_checked:
        return "approved fact must have evidence_checked=true"
    if not reviewer.strip():
        return "reviewer is required"
    return None


def apply_decision(
    payload: dict[str, Any],
    fact_id: str,
    reviewer: str,
    approved: bool,
    evidence_checked: bool,
    note: str,
) -> bool:
    items = payload.get("facts", []) + payload.get("rules", [])
    target = next((item for item in items if item.get("id") == fact_id), None)
    if target is None:
        return False

    human_approved = approved and evidence_checked and reviewer.strip().lower() != "agent"
    target["reviewer"] = reviewer
    target["needs_human"] = not human_approved
    target["authoritative"] = human_approved
    target["metadata"] = target.get("metadata", {})
    target["metadata"]["review_note"] = note
    target["metadata"]["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fact-id", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--approved", action="store_true")
    parser.add_argument("--evidence-checked", action="store_true")
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    error = validate_decision(args.reviewer, args.approved, args.evidence_checked)
    if error:
        print(f"REVIEW REJECTED: {error}")
        return 1

    payload = json.loads(STORE.read_text(encoding="utf-8"))
    if not apply_decision(
        payload, args.fact_id, args.reviewer, args.approved, args.evidence_checked, args.note
    ):
        print(f"REVIEW REJECTED: unknown fact id {args.fact_id}")
        return 1

    decisions: dict[str, Any] = {}
    if DECISIONS.exists():
        decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
    decisions[args.fact_id] = {
        "reviewer": args.reviewer,
        "approved": args.approved,
        "evidence_checked": args.evidence_checked,
        "note": args.note,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
    }

    STORE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    DECISIONS.write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"REVIEW SAVED: {args.fact_id} by {args.reviewer} approved={args.approved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""DOCX-first review: auto-accept invariant-passing rows, flag the rest.

The reviewer works from DOCX cell text, not from a raw PDF render. PDF images
are kept only as tie-breaker evidence for flagged rows. Nothing here claims
human review: accepted rows carry authoritative_source='vietnamocr_docx'.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

STORE = ROOT / "data" / "canonical" / "medical_scores_docx.json"
QUEUE = ROOT / "data" / "exports" / "review" / "canonical" / "review_queue_docx.json"
HEADER_TOKENS = ("stt", "tt", "bệnh tật", "điểm", "mục i", "mục ii", "ghi chú")
STUCK_RE = re.compile(r"\d{3,}[A-Za-z]|[A-Za-z]\d{4,}")


def invariant_errors(fact: dict[str, Any], root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        value = float(fact.get("value", 0))
    except (TypeError, ValueError):
        value = 0
    if not (1 <= value <= 6):
        errors.append("score outside 1..6")
    condition = str(fact.get("condition", ""))
    if len(condition) < 8 and not re.search(r"\d", condition):
        errors.append("condition too short")
    lowered = condition.lower()
    if any(token == lowered or lowered.startswith(token + ":") for token in HEADER_TOKENS):
        errors.append("header-like row")
    if STUCK_RE.search(condition):
        errors.append("number and text stuck together")
    evidence = str(fact.get("evidence_image", ""))
    if not evidence or not (root / evidence).exists():
        errors.append("missing evidence image")
    return errors


def apply_review(payload: dict[str, Any], root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    accepted = 0
    flagged: list[dict[str, Any]] = []
    for fact in payload.get("facts", []):
        errors = invariant_errors(fact, root)
        if errors:
            fact["authoritative"] = False
            fact["needs_human"] = True
            fact["review_needed"] = True
            fact["authoritative_source"] = None
            flagged.append({
                "id": fact.get("id"),
                "document_id": fact.get("document_id"),
                "page": fact.get("page"),
                "condition": fact.get("condition"),
                "value": fact.get("value"),
                "evidence_image": fact.get("evidence_image"),
                "errors": errors,
            })
            continue
        fact["authoritative"] = True
        fact["needs_human"] = False
        fact["review_needed"] = False
        fact["authoritative_source"] = "vietnamocr_docx"
        accepted += 1

    summary = {
        "source": "drafts/outsource/ocr-result.docx",
        "total": len(payload.get("facts", [])),
        "auto_accepted": accepted,
        "flagged": len(flagged),
        "review_basis": "DOCX cell grid; PDF image only for flagged rows",
    }
    return payload, {"summary": summary, "items": flagged}


def main() -> int:
    payload = json.loads(STORE.read_text(encoding="utf-8"))
    updated, queue = apply_review(payload)
    STORE.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(queue["summary"], ensure_ascii=False, indent=2))
    for item in queue["items"][:12]:
        print("  !", item["id"], item["errors"], "|", str(item["condition"])[:70])
    print(f"Review queue: {QUEUE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

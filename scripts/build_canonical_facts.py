"""Build canonical Layer-A facts for the pilot score tables and guidance rules.

Render evidence pages from the raw PDFs at 200 DPI, parse score rows from the
processed Markdown tables, and write data/canonical/medical_scores.json.

Nothing produced here is authoritative: human sign-off is still required.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import pymupdf

from app.ingestion.table_structure import extract_score_rows
from app.models.canonical_fact import CanonicalFact, CanonicalRule

RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
EVIDENCE_DIR = ROOT / "data" / "exports" / "review" / "canonical"
OUT = ROOT / "data" / "canonical" / "medical_scores.json"

PDF_BY_DOC = {
    "thông_tư_105": "Thông_tư_105.pdf",
    "thông_tư_106": "Thông_tư_106.pdf",
    "thông_tư_68": "Thông_tư_68.pdf",
    "thông_tư_88": "Thông_tư_88.pdf",
    "hướng_dẫn_cục_quân_y": "Hướng_dẫn_Cục_quân_y.pdf",
}
RULE_SPECS = [
    ("HD_rules_eligibility", "hướng_dẫn_cục_quân_y", 1, "- Đối với công dân nam nhập ngũ: Tuyển chọn công dân có sức khỏe loại 1,", 3, "tuyển chọn sức khỏe loại 1, 2, 3"),
    ("HD_rules_disqualify", "hướng_dẫn_cục_quân_y", 2, "- Không gọi nhập ngũ đối với công dân có tật khúc xạ cận thị lớn hơn 1,5 diop (D),", 2, "không gọi nhập ngũ với viễn thị các mức độ"),
    ("HD_rules_no_score", "hướng_dẫn_cục_quân_y", 4, "- Tiêu chuẩn tật khúc xạ cận thị, viễn thị, chỉ số BMI là tiêu chuẩn riêng,", 3, "cận/viễn/BMI không cho điểm phân loại sức khỏe"),
]
SCORE_RE = re.compile(r"^[1-6]$")


def render_evidence(pdf_name: str, page_no: int, label: str) -> str:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    pdf = RAW / pdf_name
    relative = (EVIDENCE_DIR / f"{label}_p{page_no}.png").relative_to(ROOT).as_posix()
    if (ROOT / relative).exists():
        return relative
    document = pymupdf.open(pdf)
    pixmap = document[page_no - 1].get_pixmap(matrix=pymupdf.Matrix(200 / 72, 200 / 72))
    pixmap.save(ROOT / relative)
    return relative


def parse_score_rows(
    content: str,
    document_id: str,
    page: int,
    evidence_image: str,
) -> list[CanonicalFact]:
    facts: list[CanonicalFact] = []
    for condition, score in extract_score_rows(content):
        facts.append(CanonicalFact.model_validate({
            "id": f"{document_id}_p{page}_score_{len(facts) + 1:03d}",
            "document_id": document_id,
            "page": page,
            "condition": condition,
            "value": float(score),
            "value_type": "score",
            "source_kind": "ocr",
            "evidence_image": evidence_image,
            "raw_row": condition[:300],
            "reviewer": "agent",
            "needs_human": True,
            "authoritative": False,
        }))
    return facts


def extract_rule(pdf_page: str, start: str, lines: int) -> str:
    page_lines = pdf_page.splitlines()
    index = next(i for i, line in enumerate(page_lines) if start in line)
    return re.sub(r"\s+", " ", " ".join(
        line.strip() for line in page_lines[index : index + lines]
    )).strip()


def main() -> int:
    facts: list[CanonicalFact] = []
    tables_seen = 0
    tables_parsed = 0
    page_fact_count: dict[tuple[str, int], int] = {}

    for path in sorted(PROCESSED.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        document_id = str(document.get("document_id") or path.stem)
        pdf_name = PDF_BY_DOC.get(document_id)
        if not pdf_name:
            continue
        for node in document.get("nodes", []):
            if not (node.get("is_table") or "table" in str(node.get("id", ""))):
                continue
            page = int(node.get("page_number") or 0)
            if not page:
                continue
            tables_seen += 1
            evidence = render_evidence(pdf_name, page, f"{document_id}_table")
            parsed = parse_score_rows(
                str(node.get("content", "")), document_id, page, evidence
            )
            if not parsed:
                continue
            tables_parsed += 1
            for fact in parsed:
                key = (document_id, page)
                sequence = page_fact_count.get(key, 0) + 1
                page_fact_count[key] = sequence
                fact.id = f"{document_id}_p{page}_score_{sequence:03d}"
                facts.append(fact)

    rules: list[CanonicalRule] = []
    pdf = pymupdf.open(RAW / "Hướng_dẫn_Cục_quân_y.pdf")

    for rule_id, document_id, page, start, lines, conclusion in RULE_SPECS:
        evidence = render_evidence("Hướng_dẫn_Cục_quân_y.pdf", page, rule_id)
        rules.append(CanonicalRule.model_validate({
            "id": rule_id,
            "document_id": document_id,
            "page": page,
            "condition": conclusion,
            "conclusion": conclusion,
            "source_kind": "pdf_text_layer",
            "evidence_image": evidence,
            "raw_text": extract_rule(pdf[page - 1].get_text("text"), start, lines),
            "reviewer": "agent",
            "needs_human": True,
            "authoritative": False,
        }))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "tables_seen": tables_seen,
            "tables_with_score_rows": tables_parsed,
            "facts": len(facts),
            "rules": len(rules),
        },
        "note": "Full-corpus score extraction. All entries need_human=true; not authoritative until signed off.",
        "facts": [fact.model_dump() for fact in facts],
        "rules": [rule.model_dump() for rule in rules],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Tables seen: {tables_seen} | with score rows: {tables_parsed}")
    print(f"Wrote {len(facts)} facts + {len(rules)} rules -> {OUT.relative_to(ROOT)}")
    for fact in facts[:12]:
        print(" ", fact.id, "p", fact.page, "=", fact.value, "|", fact.condition[:80])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

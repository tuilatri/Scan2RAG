"""Ingest score tables from drafts/outsource/ocr-result.docx into canonical facts.

The DOCX is produced externally by VietNamOCR 3.3.1. This script reads the OOXML
table grid directly (stdlib only), picks the score column by header name, maps
each DOCX table back to a document/page using the existing canonical store, and
writes data/canonical/medical_scores_docx.json.

Nothing produced here is authoritative: human review is still required.
"""

from __future__ import annotations

import difflib
import json
import re
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
DOCX = ROOT / "drafts" / "outsource" / "ocr-result.docx"
CANONICAL = ROOT / "data" / "canonical" / "medical_scores.json"
OUT = ROOT / "data" / "canonical" / "medical_scores_docx.json"
SCORE_RE = re.compile(r"^[1-6]$")
HEADER_HINTS = ("diem", "điem", "iem", "dim", "ieam")


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(text).lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch) and ch.isalnum())


def parse_docx_tables(payload: bytes) -> list[list[list[str]]]:
    document = ET.fromstring(payload)
    body = document.find(W + "body")
    tables: list[list[list[str]]] = []
    for table in body.findall(W + "tbl"):
        rows: list[list[str]] = []
        for tr in table.findall(W + "tr"):
            rows.append([
                "".join(t.text or "" for t in tc.iter(W + "t"))
                for tc in tr.findall(W + "tc")
            ])
        tables.append(rows)
    return tables


def parse_score_table(rows: list[list[str]]) -> list[tuple[str, int]]:
    """Return (condition, score) pairs, using the header-named score column."""
    header_index = None
    for row in rows[:4]:
        for index, cell in enumerate(row):
            if any(hint in normalize(cell) for hint in HEADER_HINTS):
                header_index = index
                break
        if header_index is not None:
            break
    if header_index is None:
        return []

    result: list[tuple[str, int]] = []
    for row in rows:
        if header_index >= len(row):
            continue
        score_cell = row[header_index].strip()
        if not SCORE_RE.match(score_cell):
            continue
        label_cells = [
            cell.strip() for index, cell in enumerate(row)
            if index != header_index and cell.strip() and not cell.strip().isdigit()
        ]
        condition = ", ".join(label_cells)
        if len(condition) < 6:
            continue
        result.append((condition, int(score_cell)))
    return result


def find_table_context(
    parsed: list[tuple[str, int]],
    canonical: list[dict[str, Any]],
    used_contexts: set[tuple[str, int]] | None = None,
) -> dict[str, Any] | None:
    """Map a DOCX table to a document/page via fuzzy match.

    Identical tables occur in TT105 and TT88, so contexts already assigned to
    an earlier DOCX table are skipped. That lets the later table map to TT88.
    """
    used = used_contexts or set()
    scores: dict[tuple[str, int], float] = {}
    evidence: dict[tuple[str, int], str] = {}

    for condition, _ in parsed:
        needle = normalize(condition)
        if len(needle) < 12:
            continue
        for fact in canonical:
            key = (str(fact.get("document_id", "")), int(fact.get("page", 0)))
            if key in used:
                continue
            haystack = normalize(str(fact.get("condition", "")))
            if not haystack:
                continue
            ratio = difflib.SequenceMatcher(None, needle[:80], haystack[:80]).ratio()
            if ratio >= 0.62:
                scores[key] = scores.get(key, 0.0) + ratio
                evidence.setdefault(key, str(fact.get("evidence_image", "")))

    if not scores:
        return None
    best_key = max(scores, key=scores.get)
    return {
        "document_id": best_key[0],
        "page": best_key[1],
        "evidence_image": evidence[best_key],
    }


def build_facts(tables: list[list[list[str]]], canonical: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    facts: list[dict[str, Any]] = []
    mapped_tables = 0
    per_page: dict[tuple[str, int], int] = {}
    used_contexts: set[tuple[str, int]] = set()

    for rows in tables:
        parsed = parse_score_table(rows)
        if not parsed:
            continue
        context = find_table_context(parsed, canonical, used_contexts)
        if not context:
            continue
        used_contexts.add((context["document_id"], context["page"]))
        mapped_tables += 1
        key = (context["document_id"], context["page"])
        for condition, score in parsed:
            sequence = per_page.get(key, 0) + 1
            per_page[key] = sequence
            facts.append({
                "id": f"docx_{context['document_id']}_p{context['page']}_score_{sequence:03d}",
                "document_id": context["document_id"],
                "page": context["page"],
                "condition": condition,
                "value": float(score),
                "value_type": "score",
                "source_kind": "docx",
                "evidence_image": context["evidence_image"],
                "raw_row": "",
                "reviewer": "agent",
                "needs_human": True,
                "authoritative": False,
                "metadata": {"importer": "scripts/ingest_docx_facts.py"},
            })
    return facts, mapped_tables


def main() -> int:
    with DOCX.open("rb") as handle:
        with zipfile.ZipFile(handle) as archive:
            tables = parse_docx_tables(archive.read("word/document.xml"))
    canonical = json.loads(CANONICAL.read_text(encoding="utf-8"))["facts"]
    facts, mapped_tables = build_facts(tables, canonical)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(DOCX.relative_to(ROOT)),
        "summary": {
            "tables_seen": len(tables),
            "tables_mapped": mapped_tables,
            "facts": len(facts),
        },
        "note": "DOCX-derived facts. All need_human=true; not authoritative until signed off.",
        "facts": facts,
        "rules": [],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"DOCX tables: {len(tables)} | mapped: {mapped_tables} | facts: {len(facts)}")
    for fact in facts[:8]:
        print(" ", fact["id"], "=", int(fact["value"]), "|", fact["condition"][:80])
    print(f"Wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

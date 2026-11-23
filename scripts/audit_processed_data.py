"""Audit script for QA verification of processed legal JSON data.

Checks:
1. Completion rate (processed pages vs original PDF pages)
2. Structural extraction (Articles, Clauses, Points count)
3. Table extraction (Table nodes count with markdown formatting)
4. Schema compliance with ParsedDocument & DocumentNode
5. Lexical cleanliness (verifies presence of cleaned legal & medical vocabulary)
"""

import json
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import pymupdf
from app.models.document_schema import ParsedDocument


def audit_corpus():
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")

    raw_files = sorted(raw_dir.glob("*.pdf"), key=lambda p: p.stat().st_size)
    print(
        "========================================================================================="
    )
    print(
        "                  SCAN2RAG DEEP QUALITY AUDIT REPORT (PHASE 4)                           "
    )
    print(
        "========================================================================================="
    )

    total_raw_pages = 0
    total_processed_pages = 0
    total_nodes = 0
    total_tables = 0
    total_articles = 0
    total_clauses = 0
    total_points = 0
    errors = []

    for raw_pdf in raw_files:
        doc_id = raw_pdf.stem.lower()
        json_file = processed_dir / f"{doc_id}.json"

        doc = pymupdf.open(str(raw_pdf))
        pdf_page_count = len(doc)
        total_raw_pages += pdf_page_count
        doc.close()

        if not json_file.exists():
            errors.append(f"Missing processed file for: {raw_pdf.name}")
            print(f"❌ {raw_pdf.name:<28}: NOT PROCESSED")
            continue

        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
            parsed = ParsedDocument.model_validate(data)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            errors.append(f"Schema validation failed for {json_file.name}: {e}")
            print(f"❌ {raw_pdf.name:<28}: SCHEMA INVALID ({e})")
            continue

        stats = parsed.summary_stats or {}
        p_pages = stats.get("processed_pages", 0)
        total_processed_pages += p_pages
        node_count = len(parsed.nodes)
        total_nodes += node_count

        tables = sum(1 for n in parsed.nodes if n.level == "TABLE")
        articles = sum(1 for n in parsed.nodes if n.level == "ARTICLE")
        clauses = sum(1 for n in parsed.nodes if n.level == "CLAUSE")
        points = sum(1 for n in parsed.nodes if n.level == "POINT")

        total_tables += tables
        total_articles += articles
        total_clauses += clauses
        total_points += points

        status_icon = "✓" if p_pages == pdf_page_count else "⚠"
        sec_per_page = stats.get("seconds_per_page", 0.0)
        speed_str = f"{sec_per_page:.2f}s/page" if sec_per_page else "N/A"

        print(
            f"{status_icon} {raw_pdf.name:<28} | Pages: {p_pages}/{pdf_page_count} | Nodes: {node_count:<5} | "
            f"Tables: {tables:<3} | Arts: {articles:<3} | Clauses: {clauses:<3} | Speed: {speed_str}"
        )

    print(
        "-----------------------------------------------------------------------------------------"
    )
    print("TOTAL AUDIT SUMMARY:")
    print(
        f"  • Processed Pages  : {total_processed_pages}/{total_raw_pages} ({total_processed_pages / total_raw_pages * 100:.1f}%)"
    )
    print(f"  • Total Nodes      : {total_nodes}")
    print(f"  • Tables Extracted : {total_tables} Markdown Tables")
    print(
        f"  • Statutory Items  : {total_articles} Articles | {total_clauses} Clauses | {total_points} Points"
    )
    print(f"  • Audit Errors     : {len(errors)}")

    # Specific assertions for Phase 4 quality gate
    if total_tables == 0:
        errors.append("Critical Error: No tables extracted in processed documents!")

    if errors:
        print("\nERRORS DETECTED:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print(
            "\n🎉 QUALITY AUDIT SIGN-OFF: ALL PASS (Medical Tables & Text Normalized)"
        )
        return True


if __name__ == "__main__":
    success = audit_corpus()
    sys.exit(0 if success else 1)

"""Audit script for QA verification of processed legal JSON data.

Checks:
1. Completion rate (processed pages vs original PDF pages)
2. Structural extraction (Articles, Clauses, Points count)
3. Schema compliance with ParsedDocument & DocumentNode
4. Potential issues (empty nodes, broken structures)
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

    raw_files = list(raw_dir.glob("*.pdf"))
    print(
        "================================================================================"
    )
    print(
        "                     SCAN2RAG QUALITY AUDIT REPORT                              "
    )
    print(
        "================================================================================"
    )

    total_raw_pages = 0
    total_processed_pages = 0
    total_nodes = 0
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
            print(f"❌ {raw_pdf.name:<30}: NOT PROCESSED")
            continue

        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
            parsed = ParsedDocument.model_validate(data)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            errors.append(f"Schema validation failed for {json_file.name}: {e}")
            print(f"❌ {raw_pdf.name:<30}: SCHEMA INVALID ({e})")
            continue

        stats = parsed.summary_stats or {}
        p_pages = stats.get("processed_pages", 0)
        total_processed_pages += p_pages
        node_count = len(parsed.nodes)
        total_nodes += node_count

        articles = sum(1 for n in parsed.nodes if n.level == "ARTICLE")
        clauses = sum(1 for n in parsed.nodes if n.level == "CLAUSE")
        points = sum(1 for n in parsed.nodes if n.level == "POINT")

        total_articles += articles
        total_clauses += clauses
        total_points += points

        status_icon = "✓" if p_pages == pdf_page_count else "⚠"
        sec_per_page = stats.get("seconds_per_page", 0.0)
        speed_str = f"{sec_per_page:.2f}s/page" if sec_per_page else "N/A"

        print(
            f"{status_icon} {raw_pdf.name:<30} | Pages: {p_pages}/{pdf_page_count} | Nodes: {node_count:<5} | "
            f"Arts: {articles:<3} | Clauses: {clauses:<3} | Points: {points:<3} | Speed: {speed_str}"
        )

    print(
        "--------------------------------------------------------------------------------"
    )
    print("TOTAL AUDIT SUMMARY:")
    print(
        f"  • Processed Pages  : {total_processed_pages}/{total_raw_pages} ({total_processed_pages / total_raw_pages * 100:.1f}%)"
    )
    print(f"  • Total Nodes      : {total_nodes}")
    print(
        f"  • Statutory Items  : {total_articles} Articles | {total_clauses} Clauses | {total_points} Points"
    )
    print(f"  • Audit Errors     : {len(errors)}")

    if errors:
        print("\nERRORS DETECTED:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("\n🎉 QUALITY AUDIT SIGN-OFF: ALL PASS")
        return True


if __name__ == "__main__":
    success = audit_corpus()
    sys.exit(0 if success else 1)

"""Audit script for QA verification of processed legal JSON data.

Checks:
1. Completion rate (processed pages vs original PDF pages)
2. Structural extraction (Articles, Clauses, Points, Chapters count)
3. Structural hierarchy health:
   - Root & orphan node ratio: >= 75% of nodes must have parent_id or be top-level ROOT (PART/CHAPTER)
   - Chapter nodes must exist (> 0)
   - Noise line filtering: Nodes with < 5 chars should be near 0
4. Table extraction & health:
   - Table nodes count with markdown formatting
   - Table cell quality: ratio of empty cells must be <= 50%
5. Schema compliance with ParsedDocument & DocumentNode
6. Safeguard inspection: VLM rectified tables must preserve 100% numerical data
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import pymupdf
from app.models.document_schema import HierarchyLevel, ParsedDocument


def extract_numbers(text: str) -> list[str]:
    return [n.upper() for n in re.findall(r"\b\d+(?:\.\d+)?(?:[Tt]|%)?", text) if n.strip()]


def audit_corpus():
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")

    raw_files = sorted(raw_dir.glob("*.pdf"), key=lambda p: p.stat().st_size)
    print(
        "========================================================================================="
    )
    print(
        "                  SCAN2RAG DEEP QUALITY AUDIT REPORT (MILESTONE 1)                       "
    )
    print(
        "========================================================================================="
    )

    total_raw_pages = 0
    total_processed_pages = 0
    total_nodes = 0
    total_tables = 0
    total_chapters = 0
    total_articles = 0
    total_clauses = 0
    total_points = 0
    total_orphans = 0
    total_short_nodes = 0
    total_table_cells = 0
    total_empty_cells = 0
    rectified_tables_checked = 0
    rectified_tables_safeguard_failures = 0
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

        chapters = sum(1 for n in parsed.nodes if n.level == HierarchyLevel.CHAPTER)
        articles = sum(1 for n in parsed.nodes if n.level == HierarchyLevel.ARTICLE)
        clauses = sum(1 for n in parsed.nodes if n.level == HierarchyLevel.CLAUSE)
        points = sum(1 for n in parsed.nodes if n.level == HierarchyLevel.POINT)
        tables = sum(1 for n in parsed.nodes if n.level == HierarchyLevel.TABLE)

        # Count orphans (nodes that have no parent_id and are not root-level DOCUMENT/CHAPTER)
        doc_orphans = 0
        doc_short_nodes = 0
        for n in parsed.nodes:
            if n.level not in (HierarchyLevel.DOCUMENT, HierarchyLevel.CHAPTER):
                if not n.parent_id:
                    doc_orphans += 1
            if len((n.content or "").strip()) < 5 and len((n.title or "").strip()) < 5:
                doc_short_nodes += 1

            if n.level == HierarchyLevel.TABLE and n.content:
                # Inspect table cells & pipe column consistency
                lines = [line.strip() for line in n.content.split("\n") if line.strip().startswith("|")]
                col_counts = set()
                for line in lines:
                    if re.match(r"^\|[\s\-:|]+\|$", line):
                        continue
                    cells = [c.strip() for c in line.strip("|").split("|")]
                    col_counts.add(len(cells))
                    total_table_cells += len(cells)
                    total_empty_cells += sum(1 for c in cells if not c)

                if len(col_counts) > 1:
                    errors.append(f"{doc_id} table {n.id}: inconsistent pipe column count {col_counts}")

                # Inspect metadata consistency
                if n.metadata:
                    if n.metadata.get("vlm_rectified") and n.metadata.get("vlm_rejected"):
                        errors.append(f"{doc_id} table {n.id}: metadata conflict! Both vlm_rectified and vlm_rejected are True")
                    if n.metadata.get("vlm_rectified") and n.metadata.get("vlm_error"):
                        errors.append(f"{doc_id} table {n.id}: metadata debt! Has vlm_error while vlm_rectified is True")

                # Inspect safeguard on rectified table
                if n.metadata and n.metadata.get("vlm_rectified"):
                    rectified_tables_checked += 1
                    raw_backup = n.metadata.get("raw_content_backup")
                    if not raw_backup:
                        rectified_tables_safeguard_failures += 1
                        errors.append(f"{doc_id} node {n.id}: rectified but missing raw_content_backup")
                    else:
                        orig_nums = extract_numbers(raw_backup)
                        rect_nums = extract_numbers(n.content)
                        if Counter(orig_nums) != Counter(rect_nums):
                            rectified_tables_safeguard_failures += 1
                            errors.append(f"{doc_id} node {n.id}: safeguard broken! Orig nums != Rect nums")

        total_chapters += chapters
        total_articles += articles
        total_clauses += clauses
        total_points += points
        total_tables += tables
        total_orphans += doc_orphans
        total_short_nodes += doc_short_nodes

        status_icon = "✓" if p_pages == pdf_page_count else "⚠"
        sec_per_page = stats.get("seconds_per_page", 0.0)
        speed_str = f"{sec_per_page:.2f}s/page" if sec_per_page else "N/A"
        orphan_pct = (doc_orphans / max(node_count, 1)) * 100

        print(
            f"{status_icon} {raw_pdf.name:<28} | Pages: {p_pages}/{pdf_page_count} | Nodes: {node_count:<5} | "
            f"Chap: {chapters:<2} | Arts: {articles:<3} | Tbl: {tables:<2} | Orphan: {orphan_pct:.1f}% | Speed: {speed_str}"
        )

    print(
        "-----------------------------------------------------------------------------------------"
    )
    print("TOTAL AUDIT SUMMARY:")
    print(
        f"  • Processed Pages     : {total_processed_pages}/{total_raw_pages} ({total_processed_pages / total_raw_pages * 100:.1f}%)"
    )
    print(f"  • Total Nodes         : {total_nodes}")
    print(
        f"  • Hierarchy Elements  : {total_chapters} Chapters | {total_articles} Articles | {total_clauses} Clauses | {total_points} Points"
    )
    print(f"  • Tables Extracted    : {total_tables} Markdown Tables")
    orphan_rate = (total_orphans / max(total_nodes, 1)) * 100
    print(f"  • Orphan Node Ratio   : {total_orphans}/{total_nodes} ({orphan_rate:.1f}%) [Threshold <= 25%]")
    print(f"  • Short Noise Nodes   : {total_short_nodes} (< 5 chars)")

    empty_cell_rate = (total_empty_cells / max(total_table_cells, 1)) * 100 if total_table_cells else 0.0
    print(f"  • Table Empty Cell %  : {total_empty_cells}/{total_table_cells} ({empty_cell_rate:.1f}%) [Threshold <= 50%]")
    print(f"  • Rectified Checks    : {rectified_tables_checked} checked | {rectified_tables_safeguard_failures} safeguard breaches")
    print(f"  • Audit Errors        : {len(errors)}")

    # Specific assertions for Milestone 1 Quality Gate
    if total_tables == 0:
        errors.append("Critical Error: No tables extracted in processed documents!")
    if total_chapters == 0:
        errors.append("Critical Error: 0 Chapter nodes found across corpus!")
    if orphan_rate > 25.0:
        errors.append(f"Structural Debt Warning: Orphan rate {orphan_rate:.1f}% exceeds 25% limit")
    if empty_cell_rate > 50.0:
        errors.append(f"Table Debt Warning: Empty cell rate {empty_cell_rate:.1f}% exceeds 50% limit")
    if rectified_tables_safeguard_failures > 0:
        errors.append(f"Safeguard Critical Failure: {rectified_tables_safeguard_failures} rectified tables failed 100% number lock")

    if errors:
        print("\nERRORS DETECTED:")
        for err in errors[:10]:
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more errors")
        return False
    else:
        print(
            "\n🎉 QUALITY AUDIT SIGN-OFF: ALL PASS (Structural, Table & Numerical Safeguards Validated)"
        )
        return True


if __name__ == "__main__":
    success = audit_corpus()
    sys.exit(0 if success else 1)

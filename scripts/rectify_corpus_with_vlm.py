"""Corpus Rectification Runner using Qwen-VL.

Iterates over processed JSON files in data/processed/, finds TABLE nodes
needing cleanup, renders the corresponding PDF page, sends image + text to
Qwen-VL in LM Studio, records accuracy/change stats, and writes back cleanly rectified content.
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import pymupdf
from app.ingestion.vlm_rectifier import VLMVerifier


def rectify_document_tables(
    pdf_path: Path,
    json_path: Path,
    verifier: VLMVerifier,
    max_tables: int | None = None,
) -> dict:
    doc_name = pdf_path.stem.replace("_", " ")
    print(f"\n========================================================")
    print(f"Rectifying Tables with Qwen-VL: {doc_name} ({pdf_path.name})")
    print(f"========================================================")

    stats = {
        "doc_name": doc_name,
        "total_tables": 0,
        "rectified_count": 0,
        "rejected_count": 0,
        "skipped_count": 0,
        "total_time_seconds": 0.0,
    }

    if not json_path.exists():
        print(f"JSON file {json_path} does not exist.")
        return stats

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    nodes = data.get("nodes", [])
    table_nodes = [n for n in nodes if n.get("level") == "TABLE"]
    stats["total_tables"] = len(table_nodes)
    print(f"Found {len(table_nodes)} TABLE nodes in {json_path.name}")

    if not table_nodes:
        print("No TABLE nodes to rectify.")
        return stats

    doc = pymupdf.open(str(pdf_path))
    tables_to_process = table_nodes[:max_tables] if max_tables else table_nodes
    start_all = time.time()

    for idx, t_node in enumerate(tables_to_process):
        page_num = t_node["page_number"]
        metadata = t_node.get("metadata", {})

        if metadata.get("vlm_rectified"):
            print(f"  [{idx+1}/{len(tables_to_process)}] Page {page_num}: Already rectified. Skipping.")
            stats["skipped_count"] += 1
            continue

        print(f"\n  [{idx+1}/{len(tables_to_process)}] Processing Page {page_num} Table ({t_node['title']})...")
        start_t = time.time()

        page = doc[page_num - 1]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("jpeg")

        raw_content = t_node["content"]
        res = verifier.rectify_page_content(
            image_bytes=img_bytes,
            raw_content=raw_content,
            content_type="TABLE",
        )
        elapsed = time.time() - start_t

        if res["success"]:
            t_node.setdefault("metadata", {})["raw_content_backup"] = raw_content
            t_node["content"] = res["content"]
            t_node["metadata"]["vlm_rectified"] = True
            t_node["metadata"]["vlm_model"] = verifier.model_name
            t_node["metadata"]["rectify_time_sec"] = round(elapsed, 2)
            stats["rectified_count"] += 1
            print(f"    ✓ [ACCEPTED] Successfully rectified Page {page_num} in {elapsed:.1f}s (Safeguards green)")
        else:
            t_node.setdefault("metadata", {})["vlm_rejected"] = True
            t_node["metadata"]["vlm_error"] = res["error"]
            stats["rejected_count"] += 1
            print(f"    ⚠ [REJECTED] Safeguard protected Page {page_num}: {res['error']}")

        # Save checkpoint to disk after each table
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    doc.close()
    stats["total_time_seconds"] = round(time.time() - start_all, 2)
    print(
        f"\n✓ Finished {doc_name}: Rectified={stats['rectified_count']}, "
        f"Rejected={stats['rejected_count']}, Skipped={stats['skipped_count']} ({stats['total_time_seconds']}s)"
    )
    return stats


def main():
    parser = argparse.ArgumentParser(description="Rectify document tables with Qwen-VL.")
    parser.add_argument("--file", type=str, default=None, help="Target PDF filename in data/raw/")
    parser.add_argument("--all", action="store_true", help="Process all target documents (TT 105, TT 106, TT 88)")
    parser.add_argument("--max-tables", type=int, default=None, help="Limit number of tables to process per doc")
    args = parser.parse_args()

    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")

    target_files = []
    if args.file:
        target_files.append(raw_dir / args.file)
    else:
        # Default order: from smallest table count to largest
        target_files = [
            raw_dir / "Thông_tư_106.pdf",  # 12 tables
            raw_dir / "Thông_tư_105.pdf",  # 43 tables
            raw_dir / "Thông_tư_88.pdf",   # 46 tables
        ]

    verifier = VLMVerifier()
    total_stats = []

    for target_pdf in target_files:
        if not target_pdf.exists():
            continue
        target_json = processed_dir / f"{target_pdf.stem.lower()}.json"
        doc_stats = rectify_document_tables(target_pdf, target_json, verifier, max_tables=args.max_tables)
        total_stats.append(doc_stats)

    print("\n========================================================")
    print("           OVERALL VLM RECTIFICATION SUMMARY            ")
    print("========================================================")
    for s in total_stats:
        print(f"• {s['doc_name']:<25}: Rectified={s['rectified_count']:<3} | Rejected={s['rejected_count']:<3} | Skipped={s['skipped_count']:<3}")


if __name__ == "__main__":
    main()

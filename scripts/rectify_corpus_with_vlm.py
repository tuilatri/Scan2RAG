"""Corpus Rectification Runner using Qwen-VL.

Iterates over processed JSON files in data/processed/, finds TABLE nodes
(or specific statutory articles) needing cleanup, renders the corresponding PDF page,
sends image + text to Qwen-VL in LM Studio, and writes back cleanly rectified content.
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
):
    doc_name = pdf_path.stem.replace("_", " ")
    print("\n========================================================")
    print(f"Rectifying Tables with Qwen-VL: {doc_name}")
    print("========================================================")

    if not json_path.exists():
        print(f"JSON file {json_path} does not exist.")
        return

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    nodes = data.get("nodes", [])
    table_nodes = [n for n in nodes if n.get("level") == "TABLE"]
    print(f"Found {len(table_nodes)} TABLE nodes in {json_path.name}")

    if not table_nodes:
        print("No TABLE nodes to rectify.")
        return

    doc = pymupdf.open(str(pdf_path))
    rectified_count = 0
    tables_to_process = table_nodes[:max_tables] if max_tables else table_nodes

    for idx, t_node in enumerate(tables_to_process):
        page_num = t_node["page_number"]
        metadata = t_node.get("metadata", {})

        if metadata.get("vlm_rectified"):
            print(
                f"  [{idx + 1}/{len(tables_to_process)}] Page {page_num}: Already rectified. Skipping."
            )
            continue

        print(
            f"\n  [{idx + 1}/{len(tables_to_process)}] Processing Page {page_num} Table ({t_node['title']})..."
        )
        start_t = time.time()

        # Render page to JPEG (dpi=150 ensures clean text without excessive token count)
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
            t_node["content"] = res["content"]
            t_node.setdefault("metadata", {})["vlm_rectified"] = True
            t_node["metadata"]["vlm_model"] = verifier.model_name
            t_node["metadata"]["rectify_time_sec"] = round(elapsed, 2)
            rectified_count += 1
            print(f"    ✓ Successfully rectified Page {page_num} in {elapsed:.1f}s")
        else:
            print(f"    ⚠ Verification skipped for Page {page_num}: {res['error']}")

        # Save checkpoint to disk after each table
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    doc.close()
    print(f"\n✓ Finished rectifying {rectified_count} tables in {json_path.name}!")


def main():
    parser = argparse.ArgumentParser(
        description="Rectify document tables with Qwen-VL."
    )
    parser.add_argument(
        "--file",
        type=str,
        default="Thông_tư_105.pdf",
        help="Target PDF filename in data/raw/",
    )
    parser.add_argument(
        "--max-tables", type=int, default=None, help="Limit number of tables to process"
    )
    args = parser.parse_args()

    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")

    target_pdf = raw_dir / args.file
    target_json = processed_dir / f"{target_pdf.stem.lower()}.json"

    verifier = VLMVerifier()
    rectify_document_tables(
        target_pdf, target_json, verifier, max_tables=args.max_tables
    )


if __name__ == "__main__":
    main()

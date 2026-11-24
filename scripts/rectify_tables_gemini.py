"""Corpus Rectification Runner using Google Gemini (Google AI Studio).

Iterates over processed JSON files in data/processed/, finds unrectified TABLE nodes,
renders the corresponding PDF page, sends image + text to Google Gemini (gemini-3.5-flash),
strictly verifies 100% numerical invariance (Counter(orig) == Counter(rect)),
and writes back clean Markdown tables with metadata.
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

import pymupdf

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def extract_numbers(text: str) -> list[str]:
    """Extract all numeric tokens including decimals and letters (e.g., 1.5D, 3T)."""
    return [n.upper() for n in re.findall(r"\b\d+(?:[\.,]\d+)?(?:[a-zA-Z]+)?\b", text)]


def call_gemini_vision(
    api_key: str,
    model_name: str,
    image_bytes: bytes,
    table_text: str,
    max_retries: int = 3,
) -> tuple[bool, str]:
    """Call Google AI Studio generateContent REST API with image and prompt."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = f"""Bạn là một chuyên gia hiệu đính tài liệu y tế và pháp lý quân sự Việt Nam.
Dưới đây là một bảng biểu được trích xuất bằng OCR nhưng cấu trúc Markdown hoặc dấu tiếng Việt có thể chưa chuẩn:

--- TEXT OCR GỐC ---
{table_text}
--------------------

Hãy quan sát kỹ ảnh trang tài liệu đính kèm và hiệu đính bảng trên:
1. Đảm bảo chuẩn bảng Markdown (bắt đầu và kết thúc mỗi dòng bằng dấu |, hàng tiêu đề phân cách |---|).
2. KHÔNG ĐƯỢC LÀM MẤT HOẶC TỰ BỊA BẤT KỲ CON SỐ NÀO (bao gồm cả số thứ tự, điểm khám, ký hiệu như 1, 2, 3, 4, 5, 6, 1.5D, 3T, v.v.).
3. Khôi phục đúng dấu tiếng Việt chính xác theo ảnh gốc (Cận thị, Viễn thị, Loạn thị, v.v.).
4. Chỉ trả về duy nhất khối bảng Markdown, không giải thích gì thêm."""

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": img_b64
                    }
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096,
        }
    }

    req_data = json.dumps(payload).encode("utf-8")

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if not candidates:
                    return False, "Gemini returned no candidates"
                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                
                # Clean markdown blocks if enclosed in ```markdown ... ```
                text = re.sub(r"^```markdown\s*", "", text, flags=re.MULTILINE)
                text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
                text = text.strip()
                return True, text
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            if e.code == 503 or e.code == 429:
                sleep_time = (attempt + 1) * 3
                print(f"      [Retry {attempt+1}/{max_retries}] HTTP {e.code}. Waiting {sleep_time}s...")
                time.sleep(sleep_time)
                continue
            return False, f"HTTP {e.code}: {err_body[:200]}"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return False, str(e)

    return False, "Exceeded max retries"


def rectify_document_gemini(
    pdf_path: Path,
    json_path: Path,
    api_key: str,
    model_name: str,
    max_tables: int | None = None,
) -> dict:
    doc_name = pdf_path.stem.replace("_", " ")
    print("\n========================================================")
    print(f"Rectifying Tables with Gemini ({model_name}): {pdf_path.name}")
    print("========================================================")

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
        return stats

    doc = pymupdf.open(str(pdf_path))
    tables_to_process = table_nodes[:max_tables] if max_tables else table_nodes
    start_all = time.time()

    for idx, t_node in enumerate(tables_to_process):
        page_num = t_node["page_number"]
        metadata = t_node.get("metadata", {})

        # Skip already rectified tables
        if metadata.get("vlm_rectified"):
            stats["skipped_count"] += 1
            continue

        orig_content = t_node.get("content", "")
        orig_nums = extract_numbers(orig_content)

        print(f"  [{idx+1}/{len(tables_to_process)}] Processing Page {page_num} ({t_node['id']}) [Orig numbers: {len(orig_nums)}]")

        # Render page
        page_idx = page_num - 1
        if page_idx < 0 or page_idx >= len(doc):
            print(f"    Page index {page_idx} out of range.")
            continue

        page = doc[page_idx]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")

        t0 = time.time()
        success, rect_text = call_gemini_vision(api_key, model_name, img_bytes, orig_content)
        elapsed = time.time() - t0

        if not success:
            print(f"    FAILED call Gemini: {rect_text}")
            stats["rejected_count"] += 1
            metadata["vlm_error"] = rect_text
            continue

        # Safeguard Check: 100% number preservation
        rect_nums = extract_numbers(rect_text)
        orig_counter = Counter(orig_nums)
        rect_counter = Counter(rect_nums)

        if orig_counter == rect_counter:
            print(f"    ACCEPTED ({elapsed:.2f}s) - 100% Numbers Preserved ({len(rect_nums)} nums)")
            if "raw_content_backup" not in metadata:
                metadata["raw_content_backup"] = orig_content
            t_node["content"] = rect_text
            metadata["vlm_rectified"] = True
            metadata["vlm_rejected"] = False
            metadata["rectified_model"] = model_name
            metadata["safeguard_passed"] = True
            metadata["vlm_error"] = None
            stats["rectified_count"] += 1
        else:
            diff_missing = orig_counter - rect_counter
            diff_added = rect_counter - orig_counter
            err_parts = []
            if diff_missing:
                err_parts.append(f"Mất số: {[f'{k} (mất {v})' for k, v in diff_missing.items()]}")
            if diff_added:
                err_parts.append(f"Tự bịa số lạ: {[f'{k} (thêm {v})' for k, v in diff_added.items()]}")
            err_str = "; ".join(err_parts)
            print(f"    REJECTED Safeguard: {err_str}")
            metadata["vlm_rectified"] = False
            metadata["vlm_rejected"] = True
            metadata["rectified_model"] = model_name
            metadata["vlm_error"] = f"Safeguard vi phạm: {err_str}"
            stats["rejected_count"] += 1

        # Save checkpoint after each table
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Brief pause to respect API rate limits
        time.sleep(1.0)

    doc.close()
    stats["total_time_seconds"] = round(time.time() - start_all, 2)
    print(f"\nCompleted {doc_name}: Rectified={stats['rectified_count']}, Rejected={stats['rejected_count']}, Skipped={stats['skipped_count']} ({stats['total_time_seconds']}s)")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Rectify tables in corpus using Google Gemini API")
    parser.add_argument("--doc", type=str, default=None, help="Specific document stem to process")
    parser.add_argument("--max-tables", type=int, default=None, help="Limit number of tables")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

    if not api_key:
        print("ERROR: GEMINI_API_KEY not found in environment or .env file.")
        sys.exit(1)

    print(f"Loaded Gemini Configuration: Model={model_name}")

    data_dir = Path("data")
    raw_dir = data_dir / "raw"
    processed_dir = data_dir / "processed"

    docs = [
        ("Thông_tư_105.pdf", "thông_tư_105.json"),
        ("Thông_tư_106.pdf", "thông_tư_106.json"),
        ("Thông_tư_88.pdf", "thông_tư_88.json"),
    ]

    total_stats = []
    for pdf_name, json_name in docs:
        if args.doc and args.doc.lower() not in pdf_name.lower():
            continue
        pdf_path = raw_dir / pdf_name
        json_path = processed_dir / json_name
        if pdf_path.exists() and json_path.exists():
            s = rectify_document_gemini(pdf_path, json_path, api_key, model_name, max_tables=args.max_tables)
            total_stats.append(s)

    print("\n================== GEMINI RECTIFICATION RUN FINISHED ==================")
    for s in total_stats:
        print(f"• {s['doc_name']}: Rectified={s['rectified_count']} | Rejected={s['rejected_count']} | Skipped={s['skipped_count']} in {s['total_time_seconds']}s")


if __name__ == "__main__":
    main()

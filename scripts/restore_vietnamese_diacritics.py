"""Restore Vietnamese Diacritics on Text Nodes (Audit B-C4).

Workflow:
1. Local-First (--mode local): LM Studio qwen3-vl-4b (http://localhost:1234/v1) + dictionary.
2. Cloud-Verify (--mode groq): Groq llama-3.3-70b-versatile for remaining flagged nodes.
3. Strict Guards: 100% number-lock + word-count tolerance + SequenceMatcher similarity >= 0.80.
"""

import argparse
from collections import Counter
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import re
import unicodedata
import urllib.request

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
LOCAL_MODEL = "qwen3-vl-4b"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

DICTIONARY_FIXES = {
    "Phm vi Điều chnh": "Phạm vi điều chỉnh",
    "Phm vi điều chnh": "Phạm vi điều chỉnh",
    "Khám súc khe": "Khám sức khỏe",
    "súc khe": "sức khỏe",
    "Đc lp - T do - Hnh phúc": "Độc lập - Tự do - Hạnh phúc",
    "Đc lp": "Độc lập",
    "T do": "Tự do",
    "Hnh phúc": "Hạnh phúc",
    "nghĩa v qun s": "nghĩa vụ quân sự",
    "qun s": "quân sự",
    "thc hin": "thực hiện",
    "tiu chun": "tiêu chuẩn",
    "phân loi": "phân loại",
    "bnh tt": "bệnh tật",
    "cn th": "cận thị",
    "vin th": "viễn thị",
    "lon th": "loạn thị",
    "th lc": "thị lực",
}

MISSING_DIACRITIC_RE = re.compile(
    r"\b(Phm|chnh|súc|khe|Đc|lp|Hnh|qun|thc|hin|tiu|chun|bnh|cn|vin|lon|Lut|Vit|CQNG|HOI)\b"
)


def extract_numbers(text: str) -> list[str]:
    return re.findall(r"\d+(?:[.,]\d+)?", text)


def strip_accents(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")


def passes_hallucination_guard(orig: str, updated: str) -> bool:
    """Ensure 100% number-lock, similar word count, and high character-skeleton similarity."""
    if not updated or not updated.strip():
        return False
    if Counter(extract_numbers(orig)) != Counter(extract_numbers(updated)):
        return False
    orig_words = orig.split()
    upd_words = updated.split()
    max_diff = max(2, int(len(orig_words) * 0.15))
    if abs(len(orig_words) - len(upd_words)) > max_diff:
        return False
    sim = SequenceMatcher(None, strip_accents(orig).lower(), strip_accents(updated).lower()).ratio()
    return sim >= 0.80


def call_openai_compatible(url: str, model: str, text: str, api_key: str | None = None) -> str | None:
    payload = {
        "model": model,
        "temperature": 0.0,
        "max_tokens": 1024,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Bạn là chuyên gia hiệu đính văn bản pháp luật tiếng Việt. "
                    "Hãy khôi phục dấu tiếng Việt và sửa lỗi mất chữ cái do OCR trong đoạn văn sau. "
                    "TUYỆT ĐỐI giữ nguyên 100% mọi con số, ký hiệu điều/khoản/điểm và không thêm/bớt ý. "
                    "Chỉ trả về văn bản đã sửa, không giải thích."
                ),
            },
            {"role": "user", "content": text},
        ],
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def apply_dictionary(text: str) -> str:
    for wrong, right in DICTIONARY_FIXES.items():
        if wrong in text:
            text = text.replace(wrong, right)
    return text


def main():
    from dotenv import load_dotenv
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["local", "groq"], default="local")
    parser.add_argument("--all", action="store_true", help="Scan all non-TABLE nodes (not just regex-flagged)")
    args = parser.parse_args()

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if args.mode == "groq" and not groq_key:
        print("GROQ_API_KEY not set; skipping groq mode.")
        return

    total_fixed = 0
    total_rejected_by_guard = 0

    for file_path in sorted(PROCESSED_DIR.glob("*.json")):
        if file_path.name.startswith("."):
            continue
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        nodes = data.get("nodes", [])
        if args.all:
            flagged_indices = [
                i for i, n in enumerate(nodes)
                if n.get("level") != "TABLE" and (len(n.get("content", "")) >= 15 or len(n.get("title", "")) >= 10)
            ]
        else:
            flagged_indices = [
                i for i, n in enumerate(nodes)
                if n.get("level") != "TABLE"
                and (MISSING_DIACRITIC_RE.search(n.get("title", "")) or MISSING_DIACRITIC_RE.search(n.get("content", "")))
            ]
        if not flagged_indices:
            print(f"[{file_path.name}] 0 flagged nodes (clean).", flush=True)
            continue

        print(f"[{file_path.name}] Processing {len(flagged_indices)} flagged nodes ({args.mode})...", flush=True)
        file_changed = False

        for count_idx, node_idx in enumerate(flagged_indices, start=1):
            node = nodes[node_idx]
            for field in ("title", "content"):
                orig = node.get(field, "")
                if not orig or (not args.all and not MISSING_DIACRITIC_RE.search(orig)):
                    continue

                updated = apply_dictionary(orig)
                if args.all or MISSING_DIACRITIC_RE.search(updated):
                    if args.mode == "local":
                        llm_res = call_openai_compatible(LM_STUDIO_URL, LOCAL_MODEL, updated)
                    else:
                        llm_res = call_openai_compatible(GROQ_URL, GROQ_MODEL, updated, api_key=groq_key)

                    if llm_res:
                        if passes_hallucination_guard(orig, llm_res):
                            updated = llm_res
                        else:
                            total_rejected_by_guard += 1

                updated = unicodedata.normalize("NFC", updated)
                if updated != orig and passes_hallucination_guard(orig, updated):
                    node[field] = updated
                    total_fixed += 1
                    file_changed = True

            if count_idx % 25 == 0 or count_idx == len(flagged_indices):
                pct = count_idx / len(flagged_indices) * 100
                print(f"  [{file_path.name}] {count_idx}/{len(flagged_indices)} ({pct:.1f}%) | fixed: {total_fixed}", flush=True)
                if file_changed:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Done ({args.mode}). Fixed {total_fixed} fields | Rejected by guard: {total_rejected_by_guard}.", flush=True)


if __name__ == "__main__":
    main()

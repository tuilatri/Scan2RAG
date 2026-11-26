"""Generate OCR rectification report from the processed corpus (no hardcoded claims)."""

import json
import os
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_PATH = ROOT / "data" / "benchmarks" / "ocr_comparison" / "qwen3_vl_4b_report.json"

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_processed_data import check_number_lock  # noqa: E402

files = sorted(PROCESSED_DIR.glob("*.json"))
report = {
    "description": "Aggregated OCR rectification report for all processed documents",
    "total_documents": len(files),
    "documents": {},
}

total_tables = 0
total_rectified = 0
total_rejected = 0
model_counts: Counter[str] = Counter()
safeguard_breaches = 0

for file_path in files:
    with open(file_path, encoding="utf-8") as handle:
        data = json.load(handle)
    nodes = data.get("nodes", [])
    tables = [node for node in nodes if str(node.get("level", "")).lower() == "table"]
    rectified = [node for node in tables if node.get("metadata", {}).get("vlm_rectified")]
    rejected = [node for node in tables if not node.get("metadata", {}).get("vlm_rectified")]

    total_tables += len(tables)
    total_rectified += len(rectified)
    total_rejected += len(rejected)
    for node in tables:
        meta = node.get("metadata", {})
        model_counts[str(meta.get("rectified_model", "unknown"))] += 1
        ok, _reason = check_number_lock(meta.get("raw_content_backup"), node.get("content", ""))
        if not ok:
            safeguard_breaches += 1

    report["documents"][file_path.name] = {
        "total_tables": len(tables),
        "rectified_count": len(rectified),
        "rejected_count": len(rejected),
        "rectified_ids": [node["id"] for node in rectified],
        "rejected_details": [
            {
                "id": node["id"],
                "page": node.get("page_number"),
                "error": node.get("metadata", {}).get("vlm_error"),
            }
            for node in rejected
        ],
    }

report["models"] = dict(model_counts)
report["summary"] = {
    "total_tables": total_tables,
    "total_rectified": total_rectified,
    "total_rejected": total_rejected,
    "rectified_rate_percent": round(total_rectified / total_tables * 100, 2) if total_tables else 0,
    "rejected_rate_percent": round(total_rejected / total_tables * 100, 2) if total_tables else 0,
    "safeguard_breaches_in_corpus": safeguard_breaches,
}

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
print(f"Wrote {OUT_PATH.relative_to(ROOT)}: {total_rectified}/{total_tables}, breaches={safeguard_breaches}")

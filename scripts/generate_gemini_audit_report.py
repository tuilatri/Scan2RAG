"""Audit Gemini-rectified tables numerically; no ground-truth claim without scan review."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_processed_data import check_number_lock  # noqa: E402

PROCESSED_DIR = ROOT / "data" / "processed"
OUT_PATH = ROOT / "data" / "benchmarks" / "ocr_comparison" / "gemini_auditor_report.json"

verified = 0
breaches = 0
node_ids: list[str] = []

for file_path in sorted(PROCESSED_DIR.glob("*.json")):
    with open(file_path, encoding="utf-8") as handle:
        nodes = json.load(handle).get("nodes", [])
    for node in nodes:
        if node.get("level") != "TABLE":
            continue
        model = str(node.get("metadata", {}).get("rectified_model", ""))
        if "gemini" not in model.lower():
            continue
        verified += 1
        node_ids.append(str(node.get("id")))
        ok, _reason = check_number_lock(
            node.get("metadata", {}).get("raw_content_backup"), node.get("content", "")
        )
        if not ok:
            breaches += 1

report = {
    "source": "data/processed/*.json metadata.rectified_model",
    "description": "Automated numeric audit of Gemini-rectified tables",
    "model": "gemini-auditor-ground-truth",
    "verified_count": verified,
    "numeric_breaches": breaches,
    "node_ids": node_ids,
    "limitations": "Numeric invariance only; no visual comparison against scanned pages was performed.",
}

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_PATH, "w", encoding="utf-8") as handle:
    json.dump(report, handle, ensure_ascii=False, indent=2)
print(f"Wrote {OUT_PATH.relative_to(ROOT)}: verified={verified}, breaches={breaches}")

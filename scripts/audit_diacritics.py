"""Measure residual Vietnamese diacritic errors without claiming unverified cloud checks."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_PATH = ROOT / "data" / "benchmarks" / "diacritics_verification.json"

PATTERNS = ["Đi tưng", "Gii thích", "đnh", "thuc", "mc 1"]


def main() -> None:
    hits = 0
    affected_nodes = 0
    samples = []
    for file_path in sorted(PROCESSED_DIR.glob("*.json")):
        data = json.loads(file_path.read_text(encoding="utf-8"))
        for node in data.get("nodes", []):
            content = str(node.get("content", ""))
            count = sum(len(re.findall(re.escape(pattern), content)) for pattern in PATTERNS)
            if count:
                hits += count
                affected_nodes += 1
                if len(samples) < 10:
                    samples.append({"node_id": node.get("id"), "patterns": PATTERNS[:2]})

    report = {
        "status": "not_verified",
        "reason": "No cloud verification run in this audit; count is deterministic pattern scan only.",
        "patterns": PATTERNS,
        "hits": hits,
        "affected_nodes": affected_nodes,
        "samples": samples,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"hits={hits} affected_nodes={affected_nodes} status=not_verified")


if __name__ == "__main__":
    main()

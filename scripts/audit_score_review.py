"""Gate script: medical score review with auditable exceptions."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.evaluation.ocr_vision_auditor import OcrVisionAuditor  # noqa: E402


def main() -> int:
    result = OcrVisionAuditor().audit()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("passed"):
        print(
            f"SCORE REVIEW FAILED: shifted={result.get('shifted_score_cells')} "
            f"reviewed={result.get('reviewed_exceptions')} "
            f"invalid={result.get('invalid_score_cells')}"
        )
        return 1
    print(
        f"SCORE REVIEW PASS: {result['reviewed_exceptions']} reviewed exceptions, "
        f"0 unreviewed shifted cells"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

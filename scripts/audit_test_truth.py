"""Gate: TESTING_GUIDE numbers must match measured test inventory."""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "docs/ai-context/TESTING_GUIDE.md"


def _doc_number(pattern: str) -> int | None:
    match = re.search(pattern, GUIDE.read_text(encoding="utf-8"))
    return int(match.group(1)) if match else None


def _collected_pytest() -> int | None:
    venv_python = (
        ROOT / "backend/.venv/Scripts/python.exe"
        if sys.platform == "win32"
        else ROOT / "backend/.venv/bin/python"
    )
    result = subprocess.run(
        [str(venv_python), "-m", "pytest", "backend/tests", "--collect-only", "-q"],
        cwd=ROOT, capture_output=True, text=True, timeout=180,
    )
    match = re.search(r"(\d+) tests? collected", result.stdout + result.stderr)
    return int(match.group(1)) if match else None


def main() -> int:
    errors: list[str] = []
    expected = {
        "pytest_items": _doc_number(r"Collected pytest items\s*\|\s*(\d+)"),
        "backend_files": _doc_number(r"Backend test files\s*\|\s*(\d+)"),
        "vitest_items": _doc_number(r"Frontend Vitest items\s*\|\s*(\d+)"),
        "frontend_files": _doc_number(r"Frontend test files\s*\|\s*(\d+)"),
    }
    backend_files = len(list((ROOT / "backend/tests").glob("test_*.py")))
    fe_files = list((ROOT / "frontend/tests").glob("*.test.ts")) + list((ROOT / "frontend/tests").glob("*.test.tsx"))
    frontend_items = sum(
        len(re.findall(r"\b(?:it|test)\s*\(", path.read_text(encoding="utf-8")))
        for path in fe_files
    )
    collected = _collected_pytest()

    checks = {
        "pytest_items": (expected["pytest_items"], collected),
        "backend_files": (expected["backend_files"], backend_files),
        "vitest_items": (expected["vitest_items"], frontend_items),
        "frontend_files": (expected["frontend_files"], len(fe_files)),
    }
    for key, (doc_value, real_value) in checks.items():
        if doc_value is None:
            errors.append(f"{key}:_claim_missing")
        elif real_value is None or doc_value != real_value:
            errors.append(f"{key}:{doc_value}!={real_value}")

    summary = {"checks": {k: v for k, v in checks.items()}, "errors": errors}
    print(json.dumps(summary, ensure_ascii=True))
    print("TEST TRUTH PASS" if not errors else "TEST TRUTH FAIL")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

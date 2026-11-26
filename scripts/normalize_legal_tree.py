"""Normalize legal tree metadata on processed JSON without re-running OCR/HITL."""

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from audit_processed_data import check_number_lock  # noqa: E402

PROCESSED_DIR = ROOT / "data" / "processed"
SUPERSEDED_IDS = {
    "thông_tư_105_clause_61", "thông_tư_105_clause_166", "thông_tư_105_clause_175",
    "thông_tư_105_clause_446", "thông_tư_105_clause_467", "thông_tư_105_clause_482",
    "thông_tư_105_clause_724",
}
ANCESTOR_LEVELS = {"CHAPTER", "SECTION", "ARTICLE"}


def _atomic_write(path: Path, data: Any) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    ) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
        tmp = Path(handle.name)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _normalize_table_rows(content: str) -> tuple[str, bool]:
    lines = [line for line in content.splitlines() if line.strip().startswith("|")]
    if len(lines) < 3:
        return content, False

    def cells_of(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    header = cells_of(lines[0])
    body = [cells_of(line) for line in lines[2:]]
    body = [row for row in body if any(cell for cell in row)]
    last_live = max((len(row) for row in body), default=len(header))
    width = min(len(header), last_live)
    while width > 1 and all(len(row) < width or not row[width - 1] for row in body):
        width -= 1

    def render(cells: list[str]) -> str:
        return "| " + " | ".join(cells[:width] + [""] * max(0, width - len(cells))) + " |"

    new_lines = [render(header), "| " + " | ".join(["---"] * width) + " |"] + [render(row) for row in body]
    new_content = "\n".join(new_lines)
    return new_content, new_content != content.strip()


def normalize_document(data: dict[str, Any]) -> dict[str, int]:
    stats = {"parents_fixed": 0, "superseded": 0, "consolidated": 0, "tables_compacted": 0, "numbers_skipped": 0}
    nodes = data.get("nodes", [])
    doc_id = str(data.get("document_id", ""))
    is_consolidated = doc_id == "thông_tư_88"

    last_ancestor: str | None = None
    root_id = next((str(n.get("id")) for n in nodes if n.get("level") == "DOCUMENT"), None)
    for index, node in enumerate(nodes):
        level = str(node.get("level", "")).upper()
        meta = node.setdefault("metadata", {})

        node_id = str(node.get("id", ""))
        nearer = last_ancestor if last_ancestor and last_ancestor not in (node_id, root_id) else None
        if level not in ("DOCUMENT", "CHAPTER") and (
            not node.get("parent_id") or node.get("parent_id") == root_id
        ):
            if nearer:
                node["parent_id"] = nearer
                stats["parents_fixed"] += 1
            elif root_id and root_id != node_id:
                node["parent_id"] = root_id
                stats["parents_fixed"] += 1

        if level in ANCESTOR_LEVELS:
            last_ancestor = str(node.get("id"))

        parent_id = str(node.get("parent_id", ""))
        if node_id in SUPERSEDED_IDS or parent_id in SUPERSEDED_IDS:
            meta["is_superseded"] = True
            meta["superseded_by"] = "thông_tư_106"
            stats["superseded"] += 1

        if is_consolidated:
            meta["is_consolidated"] = True
            stats["consolidated"] += 1

        if level == "TABLE":
            backup = meta.get("raw_content_backup")
            before = node.get("content", "")
            new_content, changed = _normalize_table_rows(before)
            if changed and check_number_lock(backup, new_content)[0]:
                node["content"] = new_content
                stats["tables_compacted"] += 1
            elif changed:
                stats["numbers_skipped"] += 1
    return stats


def main() -> None:
    totals = {"parents_fixed": 0, "superseded": 0, "consolidated": 0, "tables_compacted": 0, "numbers_skipped": 0}
    for file_path in sorted(PROCESSED_DIR.glob("*.json")):
        data = json.loads(file_path.read_text(encoding="utf-8"))
        stats = normalize_document(data)
        for key in totals:
            totals[key] += stats[key]
        if any(stats[key] for key in ("parents_fixed", "superseded", "consolidated", "tables_compacted")):
            _atomic_write(file_path, data)
    print(json.dumps(totals, ensure_ascii=True))


if __name__ == "__main__":
    main()

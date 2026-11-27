"""50-question acceptance harness: local/cloud models, Qdrant and LangGraph.

Run from anywhere:
    backend\\.venv\\Scripts\\python.exe scripts\\acceptance_run.py --verify-dataset
    backend\\.venv\\Scripts\\python.exe scripts\\acceptance_run.py --mode all --limit 3
    backend\\.venv\\Scripts\\python.exe scripts\\acceptance_run.py --mode all
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DATASET = SCRIPTS / "acceptance_questions.json"
PROCESSED = ROOT / "data" / "processed"
BACKEND = ROOT / "backend"
OUT_DIR = ROOT / "data" / "exports"
CHECK_QDRANT = SCRIPTS / "check_qdrant.py"

PYTHON = BACKEND / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    PYTHON = BACKEND / ".venv" / "bin" / "python"

REFUSAL_MARKERS = (
    "không có thông tin",
    "không tìm thấy",
    "không đủ căn cứ",
    "không thể",
    "xin lỗi",
    "không được cung cấp",
    "không có trong",
    "không chứa",
    "không quy định",
    "không cung cấp",
    "không có dữ liệu",
    "hoàn toàn không",
    "ngoài phạm vi",
)


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    env_file = ROOT / ".env"
    if not env_file.exists():
        return values
    for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class Server:
    def __init__(self, mode: str, prefer_local: bool, env_values: dict[str, str]) -> None:
        self.port = free_port()
        self.url = f"http://127.0.0.1:{self.port}/api/v1"
        self.log_path = OUT_DIR / f"acceptance_uvicorn_{mode}.log"
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_path.open("w", encoding="utf-8")
        child_env = os.environ.copy()
        child_env.update(env_values)
        child_env["PREFER_LOCAL"] = "true" if prefer_local else "false"
        command = [
            str(PYTHON),
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
            "--log-level",
            "warning",
        ]
        self.proc = subprocess.Popen(
            command,
            cwd=str(BACKEND),
            env=child_env,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
        )

    def wait_ready(self, timeout: float = 90.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"uvicorn exited early: see {self.log_path}")
            try:
                with urllib.request.urlopen(f"{self.url}/health", timeout=2) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(0.5)
        raise RuntimeError(f"uvicorn not ready after {timeout}s: see {self.log_path}")

    def stop(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=10)
        self.log_file.close()


def post_json(url: str, payload: dict[str, Any], api_key: str, timeout: int = 300) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def stream_answer(base_url: str, query: str, api_key: str, timeout: int = 300) -> dict[str, Any]:
    result: dict[str, Any] = {
        "answer": "",
        "citations": [],
        "statuses": [],
        "provider": "unknown",
        "model": "unknown",
        "latency_ms": 0.0,
        "error": "",
    }
    started = time.perf_counter()
    request = urllib.request.Request(
        f"{base_url}/query/stream",
        data=json.dumps({"query": query}, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "X-API-Key": api_key,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            try:
                event = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            kind = event.get("event")
            if kind == "token":
                result["answer"] += str(event.get("token", ""))
            elif kind == "citations":
                result["citations"] = event.get("citations", [])
            elif kind == "status":
                status = str(event.get("status", ""))
                if status and status not in result["statuses"]:
                    result["statuses"].append(status)
            elif kind == "done":
                result["provider"] = event.get("provider", "unknown")
                result["model"] = event.get("model", "unknown")
                result["latency_ms"] = float(event.get("latency_total_ms", 0.0))
            elif kind == "error":
                result["error"] = str(event.get("message", ""))
    if not result["latency_ms"]:
        result["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return result


def norm_doc(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text[:-4] if text.endswith(".pdf") else text


def token_present(token: str, answer: str) -> bool:
    lowered = answer.lower()
    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return re.search(r"(?<![\d.])" + re.escape(token) + r"(?![\d.])", lowered) is not None
    return token.lower() in lowered


def is_refusal(answer: str) -> bool:
    lowered = answer.lower()
    return any(marker in lowered for marker in REFUSAL_MARKERS)


def evaluate(question: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    answer = result["answer"]
    if question["expect_refusal"]:
        answer_hit = is_refusal(answer)
    else:
        answer_hit = all(token_present(token, answer) for token in question["expected_answer_tokens"])

    citations = result["citations"]
    docs = [norm_doc(c.get("document_id")) for c in citations]
    pages = {c.get("page_number") for c in citations}
    expected_docs = question["expected_document_ids"]
    expected_pages = question["expected_pages"]

    doc_hit = None
    if expected_docs:
        doc_hit = any(norm_doc(expected) in doc for expected in expected_docs for doc in docs)
    page_hit = None
    if expected_pages:
        page_hit = any(page in pages for page in expected_pages)

    return {
        "answer_hit": bool(answer_hit),
        "citation_doc_hit": doc_hit,
        "citation_page_hit": page_hit,
        "refusal_marker": is_refusal(answer),
        "secondary_cloud_used": "cloud_failed" in result["statuses"],
        "local_fallback_used": any(
            status in {"local_fallback", "offline"} for status in result["statuses"]
        ),
    }


def verify_dataset(questions: list[dict[str, Any]]) -> dict[str, Any]:
    corpus: dict[str, str] = {}
    for path in PROCESSED.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        corpus[path.stem] = "\n".join(str(node.get("content", "")) for node in data.get("nodes", []))

    failures: list[dict[str, Any]] = []
    for question in questions:
        if question["expect_refusal"]:
            continue
        for doc_id in question["expected_document_ids"]:
            if doc_id not in corpus:
                failures.append({"id": question["id"], "reason": f"missing corpus {doc_id}"})
        for token in question["expected_answer_tokens"]:
            search_space = "\n".join(corpus[doc] for doc in question["expected_document_ids"]) if question["expected_document_ids"] else "\n".join(corpus.values())
            if token.lower() not in search_space.lower():
                failures.append({"id": question["id"], "reason": f"token not in corpus: {token}"})

    return {
        "total": len(questions),
        "passed": len(questions) - len({item["id"] for item in failures}),
        "failures": failures,
    }


def load_dataset() -> list[dict[str, Any]]:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    return list(payload["questions"])


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    def ratio(key: str) -> str:
        values = [item["metrics"][key] for item in records if item["metrics"][key] is not None]
        if not values:
            return "n/a"
        return f"{sum(1 for value in values if value)}/{len(values)}"

    latencies = [item["result"]["latency_ms"] for item in records]
    return {
        "questions": len(records),
        "answer_hit": ratio("answer_hit"),
        "citation_doc_hit": ratio("citation_doc_hit"),
        "citation_page_hit": ratio("citation_page_hit"),
        "refusal_marker": ratio("refusal_marker"),
        "secondary_cloud_count": sum(1 for item in records if item["metrics"]["secondary_cloud_used"]),
        "local_fallback_count": sum(1 for item in records if item["metrics"]["local_fallback_used"]),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0,
        "providers": sorted({item["result"]["provider"] for item in records}),
    }


def run_chat_mode(mode: str, questions: list[dict[str, Any]], env_values: dict[str, str], api_key: str, limit: int) -> dict[str, Any]:
    server = Server(mode, prefer_local=(mode == "local"), env_values=env_values)
    records: list[dict[str, Any]] = []
    try:
        server.wait_ready()
        for question in questions[:limit] if limit else questions:
            result = stream_answer(server.url, question["query"], api_key)
            records.append(
                {
                    "id": question["id"],
                    "query": question["query"],
                    "expected": {
                        "document_ids": question["expected_document_ids"],
                        "pages": question["expected_pages"],
                        "tokens": question["expected_answer_tokens"],
                        "expect_refusal": question["expect_refusal"],
                    },
                    "result": result,
                    "metrics": evaluate(question, result),
                }
            )
            print(
                f"  [{mode}] {question['id']} answer={'OK' if records[-1]['metrics']['answer_hit'] else 'MISS'} "
                f"provider={result['provider']} {result['latency_ms']:.0f}ms",
                flush=True,
            )
    finally:
        server.stop()
    return {"summary": summarize(records), "records": records}


def run_qdrant() -> dict[str, Any]:
    process = subprocess.run(
        [str(PYTHON), str(CHECK_QDRANT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    output = f"{process.stdout}\n{process.stderr}".strip()
    match = re.search(r"points:\s*(\d+)", output)
    return {
        "exit_code": process.returncode,
        "pass": process.returncode == 0 and "RESULT: PASS" in output,
        "points": int(match.group(1)) if match else None,
        "expected_points": 7263,
        "output_tail": output[-1200:],
    }


def run_langgraph(questions: list[dict[str, Any]], env_values: dict[str, str], api_key: str, limit: int) -> dict[str, Any]:
    compare_questions = [item for item in questions if item["category"] == "compare"]
    if limit:
        compare_questions = compare_questions[:limit]
    if not compare_questions:
        return {"summary": {"questions": 0}, "records": []}

    server = Server("langgraph", prefer_local=False, env_values=env_values)
    records: list[dict[str, Any]] = []
    try:
        server.wait_ready()
        for question in compare_questions:
            started = time.perf_counter()
            response = post_json(
                f"{server.url}/query/compare",
                {"query": question["query"], "thread_id": f"acc-{question['id']}"},
                api_key,
                timeout=600,
            )
            latency = round((time.perf_counter() - started) * 1000, 1)
            verification = response.get("verification", {})
            record = {
                "id": question["id"],
                "query": question["query"],
                "answer": response.get("answer", ""),
                "citations_count": len(response.get("citations", [])),
                "evidence": response.get("evidence", []),
                "version_notes": response.get("version_notes", []),
                "verification": verification,
                "provider": response.get("provider", "unknown"),
                "model": response.get("model", "unknown"),
                "retry_count": response.get("retry_count", 0),
                "latency_ms": latency,
            }
            records.append(record)
            print(
                f"  [langgraph] {question['id']} verified={verification.get('passed')} "
                f"notes={len(record['version_notes'])} evidence={len(record['evidence'])} {latency:.0f}ms",
                flush=True,
            )
    finally:
        server.stop()

    summary = {
        "questions": len(records),
        "verification_passed": f"{sum(1 for item in records if item['verification'].get('passed'))}/{len(records)}",
        "with_version_notes": f"{sum(1 for item in records if item['version_notes'])}/{len(records)}",
        "with_evidence": f"{sum(1 for item in records if item['evidence'])}/{len(records)}",
        "avg_latency_ms": round(sum(item["latency_ms"] for item in records) / len(records), 1),
    }
    return {"summary": summary, "records": records}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["all", "qdrant", "local", "cloud", "langgraph"], default="all")
    parser.add_argument("--limit", type=int, default=0, help="0 = all questions")
    parser.add_argument("--ids", type=str, default="", help="comma-separated question IDs, e.g. AC-46,AC-48")
    parser.add_argument("--out", type=Path, default=OUT_DIR / "acceptance_report.json")
    parser.add_argument("--verify-dataset", action="store_true", help="only verify expectations against corpus")
    args = parser.parse_args()

    questions = load_dataset()
    if args.ids:
        wanted_ids = {item.strip() for item in args.ids.split(",") if item.strip()}
        questions = [item for item in questions if item["id"] in wanted_ids]
        if not questions:
            raise SystemExit(f"No questions matched --ids {args.ids}")
    env_values = load_env()
    api_key = env_values.get("SCAN2RAG_API_KEY", "")

    dataset_check = verify_dataset(questions)
    print(
        f"Dataset: {dataset_check['passed']}/{dataset_check['total']} expectations verified"
        f" ({len(dataset_check['failures'])} issues)",
        flush=True,
    )
    for failure in dataset_check["failures"][:20]:
        print(f"  ! {failure['id']}: {failure['reason']}", flush=True)
    if args.verify_dataset:
        return 0 if not dataset_check["failures"] else 1

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": {"file": str(DATASET.relative_to(ROOT)), "count": len(questions), "verify": dataset_check},
        "config": {
            "mode": args.mode,
            "limit": args.limit,
            "ids": args.ids,
            "prefer_local_default": env_values.get("PREFER_LOCAL", ""),
        },
        "summary": {},
        "results": {},
    }

    modes = ["qdrant", "local", "cloud", "langgraph"] if args.mode == "all" else [args.mode]
    for mode in modes:
        print(f"\n=== {mode} ===", flush=True)
        if mode == "qdrant":
            report["results"]["qdrant"] = run_qdrant()
            report["summary"]["qdrant"] = {
                "pass": report["results"]["qdrant"]["pass"],
                "points": report["results"]["qdrant"]["points"],
            }
        elif mode in {"local", "cloud"}:
            report["results"][mode] = run_chat_mode(mode, questions, env_values, api_key, args.limit)
            report["summary"][mode] = report["results"][mode]["summary"]
        else:
            report["results"][mode] = run_langgraph(questions, env_values, api_key, args.limit)
            report["summary"][mode] = report["results"][mode]["summary"]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== SUMMARY ===", flush=True)
    for mode, summary in report["summary"].items():
        print(f"{mode}: {json.dumps(summary, ensure_ascii=False)}", flush=True)
    print(f"Report: {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

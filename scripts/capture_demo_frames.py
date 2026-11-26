"""Capture silent demo frames from the real UI with deterministic stubbed API data."""

import json
import subprocess
import time
import urllib.request
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
OUT = ROOT / "data" / "exports" / "demo" / "frames"
OUT.mkdir(parents=True, exist_ok=True)
PDF_PATH = OUT.parent / "mock_page.pdf"
FONT_PATH = Path(r"C:\Windows\Fonts\segoeui.ttf")

TABLE_ID = "thông_tư_105_table_p23"
QUERY = "Cận thị từ -3D đến dưới -4D khám nghĩa vụ quân sự mấy điểm?"

CITATION = {
    "id": "chunk_0863",
    "document_id": "thông_tư_105",
    "document_name": "Thông tư 105",
    "breadcrumb": "Thông tư 105 > Chương V > Mục II > Bảng phụ lục tiêu chuẩn sức khỏe (Trang 23)",
    "page_number": 23,
    "is_table": True,
    "rerank_score": 0.8848,
    "snippet": "Cận thị từ -3D đến dưới -4D: 3 điểm",
}

TABLE_SUMMARY = {
    "id": TABLE_ID,
    "document_id": "thông_tư_105",
    "document_name": "Thông tư 105",
    "page_number": 23,
    "title": "Bảng phụ lục tiêu chuẩn sức khỏe (Trang 23)",
    "rows_count": 8,
    "cols_count": 3,
    "vlm_rectified": True,
    "hitl_approved": False,
    "hitl_rectified": False,
}

TABLE_CONTENT = (
    "| TT | Bệnh tật | Điểm |\n| --- | --- | --- |\n"
    "| 1 | Cận thị từ -3D đến dưới -4D | 3 |\n"
    "| 2 | Viễn thị từ +3D đến dưới +5D | 2 |\n"
    "| 3 | Loạn thị | 1 |\n"
)

TABLE_DETAIL = {
    **TABLE_SUMMARY,
    "content": TABLE_CONTENT,
    "raw_content_backup": "| TT | Bệnh tật | Điểm |\n| --- | --- | --- |\n| 1 | Cn th | 3 |",
    "headers": ["TT", "Bệnh tật", "Điểm"],
    "rows": [
        ["1", "Cận thị từ -3D đến dưới -4D", "3"],
        ["2", "Viễn thị từ +3D đến dưới +5D", "2"],
        ["3", "Loạn thị", "1"],
    ],
    "metadata": {"vlm_rectified": True, "safeguard_passed": True},
}


def _make_pdf() -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=1000, height=700)
    page.insert_font(fontname="segoeui", fontfile=str(FONT_PATH))
    page.insert_text((90, 120), "THÔNG TƯ 105/2023/TT-BQP", fontsize=24, fontname="segoeui")
    page.insert_text((90, 175), "Phụ lục: Tiêu chuẩn phân loại sức khỏe", fontsize=16, fontname="segoeui")
    page.insert_text((90, 225), "Trang 23 — Cận thị từ -3D đến dưới -4D: 3 điểm", fontsize=14, fontname="segoeui")
    page.insert_text((90, 275), "Bảng phụ lục tiêu chuẩn sức khỏe (DEMO DATA)", fontsize=14, fontname="segoeui")

    rows = [
        ("1", "Cận thị từ -3D đến dưới -4D", "3"),
        ("2", "Viễn thị từ +3D đến dưới +5D", "2"),
        ("3", "Loạn thị", "1"),
    ]
    for index, (number, condition, score) in enumerate(rows):
        top = 320 + index * 36
        page.draw_rect(pymupdf.Rect(90, top, 900, top + 36), color=(0.45, 0.45, 0.45), width=0.6)
        page.insert_text((100, top + 23), number, fontsize=12, fontname="segoeui")
        page.insert_text((170, top + 23), condition, fontsize=12, fontname="segoeui")
        page.insert_text((820, top + 23), score, fontsize=12, fontname="segoeui")
    doc.save(str(PDF_PATH))
    doc.close()


def render_pdf_page_png() -> bytes:
    # Prefer the real scanned TT105 page 23 from data/raw (gitignored, local only).
    real_pdf = next((ROOT / "data/raw").glob("*105*.pdf"), None)
    source = real_pdf or PDF_PATH
    with pymupdf.open(source) as document:
        page_index = 22 if real_pdf and len(document) > 22 else 0
        return document[page_index].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).tobytes("png")


def _start_vite() -> subprocess.Popen:
    proc = subprocess.Popen(
        "npm run dev -- --host 127.0.0.1 --port 5173 --strictPort",
        cwd=FRONTEND, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        try:
            urllib.request.urlopen("http://127.0.0.1:5173", timeout=1)
            return proc
        except Exception:
            time.sleep(1)
    raise RuntimeError("Vite dev server did not start")


def _sse_body() -> str:
    events = [
        {"event": "status", "status": "retrieving"},
        {"event": "citations", "citations": [CITATION], "latency_retrieval_ms": 52.3, "latency_rerank_ms": 18.7},
    ]
    tokens = ["Theo ", "Thông tư 105, ", "cận thị từ -3D ", "đến dưới -4D ", "chấm ", "3 điểm."]
    events.extend({"event": "token", "token": token} for token in tokens)
    events.append({
        "event": "done", "provider": "lm_studio_local",
        "model": "qwen2.5-1.5b-instruct", "complexity": "simple", "latency_total_ms": 1240.5,
    })
    return "".join("data: " + json.dumps(e, ensure_ascii=False) + "\n\n" for e in events)


def _html_scene(title: str, body: str) -> str:
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><style>
    body{{margin:0;background:#0f172a;color:#e2e8f0;font-family:'Segoe UI',sans-serif;height:100vh;display:flex;flex-direction:column;justify-content:center;padding:96px}}
    h1{{font-size:56px;font-weight:600;letter-spacing:-1px;margin:0 0 32px}} p{{font-size:28px;line-height:1.6;color:#94a3b8;margin:0}}
    .tag{{position:absolute;top:40px;right:56px;font-size:18px;color:#64748b;border:1px solid #334155;padding:8px 16px;border-radius:8px}}
    </style></head><body><div class="tag">DEMO DATA</div><h1>{title}</h1><p>{body}</p></body></html>"""


def main() -> None:
    _make_pdf()
    vite = _start_vite()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)

            def handle(route):
                url, method = route.request.url, route.request.method
                if "/api/v1/health" in url:
                    route.fulfill(status=200, content_type="application/json", body=json.dumps({"status": "ok"}))
                elif "/api/v1/query/stream" in url:
                    route.fulfill(status=200, content_type="text/event-stream", body=_sse_body())
                elif "/api/v1/ocr/tables/" in url and "/rectify" in url:
                    route.fulfill(status=200, content_type="application/json", body=json.dumps({"status": "success", "node_id": TABLE_ID}))
                elif "/api/v1/ocr/tables/" in url:
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(TABLE_DETAIL, ensure_ascii=False))
                elif "/api/v1/ocr/tables" in url:
                    route.fulfill(status=200, content_type="application/json", body=json.dumps([TABLE_SUMMARY], ensure_ascii=False))
                elif "/api/v1/documents/" in url and url.endswith("/pdf"):
                    # Headless Chromium has no PDF viewer plugin: serve a rendered
                    # page image so the iframe paints deterministic demo content.
                    route.fulfill(status=200, content_type="image/png", body=render_pdf_page_png())
                elif "/api/v1/documents/" in url:
                    route.fulfill(status=200, content_type="application/json", body=json.dumps({
                        "id": "thông_tư_105", "title": "Thông tư 105/2023/TT-BQP", "effective_date": "2024-01-01",
                        "is_superseded": False, "pages_count": 105, "description": "Tiêu chuẩn sức khỏe nghĩa vụ quân sự",
                    }, ensure_ascii=False))
                elif url.endswith("/api/v1/documents"):
                    route.fulfill(status=200, content_type="application/json", body="[]")
                else:
                    route.continue_()

            page.route("**/api/v1/**", handle)
            page.goto("http://127.0.0.1:5173", wait_until="networkidle")

            page.screenshot(path=str(OUT / "01_chat.png"))
            textarea = page.get_by_placeholder("Nhập câu hỏi pháp lý")
            textarea.fill(QUERY)
            textarea.press("Enter")
            page.wait_for_timeout(1200)
            page.screenshot(path=str(OUT / "02_stream.png"))

            citation = page.locator('[role="button"]').filter(has_text="Bảng phụ lục tiêu chuẩn sức khỏe").first
            if citation.count():
                citation.click()
                page.wait_for_timeout(900)
            page.screenshot(path=str(OUT / "03_pdf.png"))

            page.get_by_role("tab", name="Đối soát OCR (HITL)").click()
            page.wait_for_timeout(700)
            page.screenshot(path=str(OUT / "04_ocr_list.png"))

            cell = page.locator('[role="button"]').filter(has_text="Cận thị từ -3D").first
            if cell.count():
                cell.click()
                page.wait_for_timeout(300)
            page.screenshot(path=str(OUT / "05_ocr_edit.png"))

            metrics = browser.new_page(viewport={"width": 1440, "height": 900})
            metrics.set_content(_html_scene(
                "Kiểm chứng hệ thống",
                "11/11 gates PASS · 7.263 chunk · Top-1 retrieval 0,8855<br>Number-lock 0 breach · 24 reviewed exceptions",
            ))
            metrics.screenshot(path=str(OUT / "06_metrics.png"))

            closing = browser.new_page(viewport={"width": 1440, "height": 900})
            closing.set_content(_html_scene("Scan2RAG", "Vietnamese Document Intelligence<br>Hybrid local–cloud RAG · Silent demo — captions only"))
            closing.screenshot(path=str(OUT / "07_closing.png"))
            browser.close()
    finally:
        subprocess.run(["taskkill", "/PID", str(vite.pid), "/T", "/F"], capture_output=True)
    print(f"captured {len(list(OUT.glob('*.png')))} frames -> {OUT}")


if __name__ == "__main__":
    main()

"""Assemble silent captioned demo MP4 from captured PNG frames."""

import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FRAMES = ROOT / "data" / "exports" / "demo" / "frames"
CAPTIONED = ROOT / "data" / "exports" / "demo" / "captioned"
OUTPUT = ROOT / "data" / "exports" / "demo" / "scan2rag_demo.mp4"
CAPTIONED.mkdir(parents=True, exist_ok=True)

SCENES = [
    ("01_chat.png", 20, "Scan2RAG — hỏi đáp văn bản pháp lý tiếng Việt, có trích dẫn trang PDF"),
    ("02_stream.png", 25, "Trích dẫn hiện ngay trước câu trả lời — SSE streaming token-by-token"),
    ("03_pdf.png", 25, "Mỗi câu trả lời liên kết ngược tới đúng trang PDF gốc"),
    ("04_ocr_list.png", 35, "Rà soát con người: 111 bảng y tế, sửa ô điểm có safeguard 1–6"),
    ("05_ocr_edit.png", 30, "Phục hồi dấu tiếng Việt, bảo toàn 100% điểm số"),
    ("06_metrics.png", 25, "Kiểm chứng: 11 gate xanh · hybrid retrieval · number-lock 0 breach"),
    ("07_closing.png", 10, "Scan2RAG — Vietnamese Document Intelligence"),
]

FONT_PATH = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold and FONT_BOLD.exists() else FONT_PATH
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def main() -> None:
    entries = []
    for index, (filename, seconds, caption) in enumerate(SCENES, start=1):
        base = Image.open(FRAMES / filename).convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        bar_height = 120
        overlay_draw.rectangle(
            (0, base.height - bar_height, base.width, base.height), fill=(8, 15, 30, 245)
        )
        image = Image.alpha_composite(base, overlay).convert("RGB")
        draw = ImageDraw.Draw(image)
        draw.text((48, image.height - bar_height + 28), caption,
                  font=_font(34, bold=True), fill=(248, 250, 252))
        draw.text((48, image.height - bar_height + 78), "DEMO DATA · silent demo — captions only",
                  font=_font(20), fill=(148, 163, 184))
        target = CAPTIONED / f"frame_{index:02d}.png"
        image.save(target)
        entries.append((target, seconds))

    list_path = CAPTIONED / "concat.txt"
    lines = []
    for path, seconds in entries:
        lines.append(f"file '{path.as_posix()}'")
        lines.append(f"duration {seconds}")
    lines.append(f"file '{entries[-1][0].as_posix()}'")
    lines.append("duration 0.04")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-vf", "fps=24", "-c:v", "libx264", "-preset", "medium", "-crf", "21",
        "-pix_fmt", "yuv420p", "-an", str(OUTPUT),
    ]
    subprocess.run(command, check=True, capture_output=True)
    print(f"video={OUTPUT} size={OUTPUT.stat().st_size} bytes duration={sum(s for _, s in entries)}s")


if __name__ == "__main__":
    main()

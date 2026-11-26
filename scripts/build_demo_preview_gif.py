"""Build and verify the animated README demo preview GIF."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parent.parent
MP4 = ROOT / "docs/assets/scan2rag_demo.mp4"
GIF = ROOT / "docs/assets/demo_preview.gif"

# One sample inside each scene of the 180s demo MP4 (verified by brightness scan).
SCENE_MIDPOINTS = (10, 32.5, 57.5, 87.5, 120, 147.5, 165)
WIDTH, HEIGHT = 640, 400
COLORS = 96
FRAME_MS = 1500

MIN_FRAMES = 7
MIN_TRANSITIONS = 6
# Old static GIF: max consecutive diff 0.10; distinct scenes: min diff 2.84.
DIFF_THRESHOLD = 2.0
MIN_BRIGHTNESS = 10.0
MAX_BYTES = 1_000_000


def _rgb_frames(path: Path) -> list[Image.Image]:
    with Image.open(path) as gif:
        frames = []
        for index in range(getattr(gif, "n_frames", 1)):
            gif.seek(index)
            frames.append(gif.convert("RGB").copy())
        return frames


def check_gif(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing file"

    frames = _rgb_frames(path)
    transitions = sum(
        max(ImageStat.Stat(ImageChops.difference(first, second)).mean) > DIFF_THRESHOLD
        for first, second in zip(frames, frames[1:])
    )
    brightness = min(ImageStat.Stat(frame).mean[0] for frame in frames)
    size = path.stat().st_size
    with Image.open(path) as gif:
        loop = gif.info.get("loop")

    passed = (
        len(frames) >= MIN_FRAMES
        and transitions >= MIN_TRANSITIONS
        and brightness > MIN_BRIGHTNESS
        and size < MAX_BYTES
        and loop == 0
    )
    detail = (
        f"frames={len(frames)} transitions={transitions} "
        f"min_brightness={brightness:.1f} bytes={size} loop={loop}"
    )
    return passed, detail


def extract_stills(ffmpeg: str, mp4: Path, temp_dir: Path) -> list[Path]:
    stills = []
    for index, timestamp in enumerate(SCENE_MIDPOINTS, start=1):
        still = temp_dir / f"scene_{index:02d}.png"
        subprocess.run(
            [ffmpeg, "-y", "-ss", str(timestamp), "-i", str(mp4), "-frames:v", "1", str(still)],
            check=True,
            capture_output=True,
        )
        if not still.exists():
            raise RuntimeError(f"ffmpeg produced no frame at {timestamp}s: {still}")
        stills.append(still)
    return stills


def build_gif(stills: list[Path], destination: Path) -> None:
    frames = []
    for still in stills:
        with Image.open(still) as source:
            resized = source.convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
            frames.append(resized.quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT))
    frames[0].save(
        destination,
        save_all=True,
        append_images=frames[1:],
        duration=FRAME_MS,
        loop=0,
        optimize=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="regenerate the GIF from the demo MP4")
    parser.add_argument("--check", action="store_true", help="verify the current GIF")
    args = parser.parse_args()
    if args.build == args.check:
        parser.error("pass exactly one of --build or --check")

    if args.build:
        with tempfile.TemporaryDirectory(prefix="scan2rag-gif-") as temp_name:
            stills = extract_stills(imageio_ffmpeg.get_ffmpeg_exe(), MP4, Path(temp_name))
            build_gif(stills, GIF)

    passed, detail = check_gif(GIF)
    print(detail)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

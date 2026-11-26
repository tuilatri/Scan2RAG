"""Absolute, repo-root-relative paths for runtime data artifacts.

Using these constants keeps behaviour identical whether the process starts
from the repo root, from backend/, or from any other working directory.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
BM25_INDEX = DATA_DIR / "bm25_index.json"
QDRANT_DB = DATA_DIR / "qdrant_db"
ENV_FILE = ROOT / ".env"

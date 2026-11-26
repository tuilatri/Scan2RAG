"""Regression: runtime data paths must not depend on the process working directory."""

from pathlib import Path

from app.core.paths import BM25_INDEX, PROCESSED_DIR, ROOT
from app.retrieval.bm25_searcher import LegalBM25Searcher


def test_repo_paths_are_absolute_and_exist():
    assert ROOT.is_absolute()
    assert (ROOT / "AGENTS.md").exists()
    assert PROCESSED_DIR.is_absolute() and PROCESSED_DIR.exists()
    assert BM25_INDEX.is_absolute() and BM25_INDEX.exists()


def test_bm25_loads_from_any_cwd(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    searcher = LegalBM25Searcher()
    assert searcher.load() is True
    assert searcher.bm25 is not None

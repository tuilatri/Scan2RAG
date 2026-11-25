"""Rebuild the BM25 index artifact with the full LegalChunk contract."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "backend"))

from app.retrieval.bm25_searcher import LegalBM25Searcher  # noqa: E402
from audit_hybrid_retrieval import load_all_corpus_chunks  # noqa: E402


def main() -> None:
    chunks = load_all_corpus_chunks()
    searcher = LegalBM25Searcher()
    searcher.fit_from_chunks(chunks)
    searcher.save()
    print(f"Rebuilt BM25 index with {len(chunks)} chunks -> {searcher.index_path}")


if __name__ == "__main__":
    main()

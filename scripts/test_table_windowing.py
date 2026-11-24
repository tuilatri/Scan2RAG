import json
import sys
from pathlib import Path
from transformers import AutoTokenizer

backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.chunking.semantic_chunker import SemanticLegalChunker

tokenizer = AutoTokenizer.from_pretrained("intfloat/multilingual-e5-small")

with open("data/processed/thông_tư_105.json", "r", encoding="utf-8") as f:
    data = json.load(f)

chunker = SemanticLegalChunker(max_tokens=350)
chunks = chunker.chunk_document(data)

table_chunks = [c for c in chunks if c.is_table]
print(f"Total chunks: {len(chunks)}")
print(f"Total table chunks after windowing: {len(table_chunks)}")

oversized = []
for tc in table_chunks:
    toks = len(tokenizer.encode(tc.content))
    if toks > 512:
        oversized.append((tc.id, toks))

print(f"Oversized table chunks (>512 tokens): {len(oversized)}")
if oversized:
    print("Oversized details:", oversized[:5])
else:
    print("SUCCESS: 100% of table chunks are <= 512 tokens!")

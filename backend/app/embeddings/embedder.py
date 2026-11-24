"""Legal Document Embedder module using sentence-transformers (Milestone 2).

Specialized for multilingual-e5 models requiring 'passage: ' and 'query: ' prefixes.
Produces L2-normalized 384-dimensional dense vectors.
"""

import os
from sentence_transformers import SentenceTransformer


class LegalEmbedder:
    """Embedding generator enforcing prefix rules and L2 normalization."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small", device: str | None = None):
        self.model_name = model_name
        # Respect EMBEDDER_DEVICE env or default to CPU to protect GPU VRAM for LM Studio (KNOWN_TRAPS #1)
        self.device = device or os.getenv("EMBEDDER_DEVICE", "cpu")
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy loader for embedding model."""
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def embed_text(self, text: str, is_query: bool = False) -> list[float]:
        """Embed a single text string."""
        prefix = "query: " if is_query else "passage: "
        prefixed_text = prefix + text.strip()

        vector = self.model.encode(
            prefixed_text,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return vector.tolist()

    def embed_batch(self, texts: list[str], is_query: bool = False, batch_size: int = 32) -> list[list[float]]:
        """Embed a list of text strings in batches."""
        if not texts:
            return []

        prefix = "query: " if is_query else "passage: "
        prefixed_texts = [prefix + t.strip() for t in texts]

        vectors = self.model.encode(
            prefixed_texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return [v.tolist() for v in vectors]

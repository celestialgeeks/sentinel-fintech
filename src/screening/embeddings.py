"""Vector embedding pipeline for entity fuzzy matching against watchlists.

Uses sentence-transformers for local embeddings (no API cost).
In production, swap to OpenAI text-embedding-3-small or similar for better quality.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import — only loaded when first used
_model: Any = None


def get_embedding_model() -> Any:
    """Lazy-load the embedding model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
            logger.info("Loading embedding model: %s", model_name)
            _model = SentenceTransformer(model_name)
        except ImportError:
            logger.warning("sentence-transformers not installed — using placeholder embeddings")
            _model = _PlaceholderModel()
    return _model


class _PlaceholderModel:
    """Dummy embedding model for environments without sentence-transformers."""

    def encode(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """Return random-looking fixed-dimension vectors."""
        import hashlib
        vectors: list[list[float]] = []
        for text in texts:
            h = hashlib.sha256(text.encode()).digest()
            # 384-dim vector from hash
            vec = [float(b) / 255.0 for b in h[:384]]
            # Normalise
            norm = sum(x * x for x in vec) ** 0.5
            vec = [x / norm for x in vec]
            vectors.append(vec)
        return vectors


def embed_entities(entity_texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of entity name strings."""
    model = get_embedding_model()
    return model.encode(entity_texts, convert_to_numpy=False)  # type: ignore


def embed_transaction(text: str) -> list[float]:
    """Generate embedding for a single transaction description."""
    model = get_embedding_model()
    result = model.encode([text], convert_to_numpy=False)  # type: ignore
    return result[0]  # type: ignore


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

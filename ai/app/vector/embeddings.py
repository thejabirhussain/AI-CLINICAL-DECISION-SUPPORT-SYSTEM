"""Embedding provider abstraction."""

import logging
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    """Abstract embedding provider."""

    def __init__(self):
        self.model_name = ""
        self.vector_size = 0

    def get_embeddings(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        raise NotImplementedError

    def get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.get_embeddings([text])[0]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider."""

    def __init__(self):
        super().__init__()
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model_name = settings.openai_embed_model

        # Map model names to vector sizes
        model_sizes = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        self.vector_size = model_sizes.get(self.model_name, 1536)

    def get_embeddings(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings using OpenAI API."""
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]
            return np.array(embeddings, dtype=np.float32)
        except Exception as e:
            logger.error(f"Error generating OpenAI embeddings: {e}")
            raise


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local sentence-transformers embedding provider."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        super().__init__()
        self.model_name = model_name
        logger.info(f"Loading local embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.vector_size = self.model.get_sentence_embedding_dimension()

    def get_embeddings(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings using local model."""
        try:
            embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            return embeddings.astype(np.float32)
        except Exception as e:
            logger.error(f"Error generating local embeddings: {e}")
            raise


def get_embedding_provider() -> EmbeddingProvider:
    """Get configured embedding provider."""
    if settings.embeddings_provider == "openai":
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not set, falling back to local embeddings")
            return LocalEmbeddingProvider()
        return OpenAIEmbeddingProvider()
    else:
        return LocalEmbeddingProvider()



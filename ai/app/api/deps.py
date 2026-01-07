"""FastAPI dependencies."""

from app.core.config import settings
from app.generation.pipeline import RAGPipeline
from app.vector.qdrant_client import get_client

qdrant_client = get_client()
rag_pipeline = RAGPipeline()


def get_rag_pipeline() -> RAGPipeline:
    """Dependency for RAG pipeline."""
    return rag_pipeline



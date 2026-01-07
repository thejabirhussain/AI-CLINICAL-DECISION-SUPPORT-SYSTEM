"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class ChatMessage(BaseModel):
    """Single conversation turn."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Chat request schema."""

    query: str = Field(..., description="User query", min_length=1, max_length=2000)
    filters: Optional[dict[str, Any]] = Field(
        None, description="Optional filters for retrieval"
    )
    json: bool = Field(False, description="Return JSON response format")
    context: Optional[str] = Field(
        None, description="Optional patient/external context to inject into the query"
    )
    history: Optional[list["ChatMessage"]] = Field(
        default=None,
        description="Optional prior conversation turns for context-awareness",
    )


class Source(BaseModel):
    """Source citation schema."""

    url: HttpUrl
    title: str
    section: Optional[str] = None
    snippet: str
    char_start: int
    char_end: int
    score: float = Field(..., ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    """Chat response schema."""

    answer_text: str
    sources: list[Source]
    confidence: Literal["low", "medium", "high"]
    query_embedding_similarity: list[float] = Field(
        ..., description="Similarity scores for retrieved chunks"
    )
    follow_up_questions: list[str] = Field(
        default_factory=list, description="Context-aware related follow-up questions"
    )


class ChunkMetadata(BaseModel):
    """Chunk metadata schema."""

    chunk_id: str
    page_url: HttpUrl
    chunk_text: str
    chunk_order: int
    section_heading: Optional[str] = None
    char_offset_start: int
    char_offset_end: int
    crawl_timestamp: datetime
    content_type: Literal["html", "pdf", "faq", "form"]
    raw_html_snippet: Optional[str] = None


class VectorChunk(BaseModel):
    """Vector chunk schema for Qdrant."""

    id: str
    url: str
    title: str
    section_heading: Optional[str] = None
    text: str
    char_start: int
    char_end: int
    content_type: Literal["html", "pdf", "faq", "form"]
    crawl_ts: str  # ISO8601
    last_modified: Optional[str] = None  # ISO8601
    language: str = "en"
    embedding_model: str
    tokens: int = 0
    hash: str


class AdminStats(BaseModel):
    """Admin statistics response."""

    collection_name: str
    total_chunks: int
    last_updated: Optional[datetime] = None
    embedding_model: str
    vector_size: int


class ReindexRequest(BaseModel):
    """Reindex request schema."""

    force: bool = Field(False, description="Force reindex even if collection exists")



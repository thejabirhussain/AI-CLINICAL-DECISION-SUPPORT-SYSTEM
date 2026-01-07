"""Chat API routes."""

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi.util import get_remote_address

from app.api.deps import rag_pipeline
from app.core.schemas import ChatRequest, ChatResponse, Source
from app.core.logging import mask_pii

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    request_obj: Request,
):
    """Chat endpoint for RAG queries."""
    try:
        # Log query (mask PII)
        client_ip = get_remote_address(request_obj)
        query_masked = mask_pii(request.query)
        logger.info(f"Chat request from {client_ip}: {query_masked}")

        # Get answer from RAG pipeline
        result = rag_pipeline.answer(
            query=request.query,
            filters=request.filters,
            history=[{"role": m.role, "content": m.content} for m in (request.history or [])],
            context=request.context,
        )

        # Format sources
        sources = []
        for src in result.get("sources", []):
            sources.append(
                Source(
                    url=src["url"],
                    title=src["title"],
                    section=src.get("section"),
                    snippet=src.get("snippet", "")[:300],
                    char_start=src.get("char_start", 0),
                    char_end=src.get("char_end", 0),
                    score=min(max(src.get("score", 0.0), 0.0), 1.0),
                )
            )

        response = ChatResponse(
            answer_text=result["answer_text"],
            sources=sources,
            confidence=result["confidence"],
            query_embedding_similarity=result.get("query_embedding_similarity", []),
            follow_up_questions=result.get("follow_up_questions", []),
        )

        # Log response
        logger.info(f"Chat response: confidence={response.confidence}, sources={len(sources)}")

        return response

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


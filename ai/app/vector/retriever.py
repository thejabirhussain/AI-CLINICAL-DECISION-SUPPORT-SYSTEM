"""Vector retrieval with filtering and similarity cutoff."""

import logging
from typing import Any, Optional

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.core.config import settings

logger = logging.getLogger(__name__)


def retrieve(
    client: QdrantClient,
    collection: str,
    query_vec: np.ndarray,
    top_k: int = 30,
    cutoff: float = 0.22,
    filters: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Retrieve similar chunks from Qdrant."""
    try:
        # Build query filter if provided
        query_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                if key == "content_type":
                    conditions.append(
                        FieldCondition(key="content_type", match=MatchValue(value=value))
                    )
                elif key == "last_modified":
                    # Handle date filtering if needed
                    pass
                # Add more filter conditions as needed
            if conditions:
                query_filter = Filter(must=conditions)

        # Search
        hits = client.search(
            collection_name=collection,
            query_vector=query_vec.tolist(),
            limit=top_k,
            with_payload=True,
            query_filter=query_filter,
            score_threshold=cutoff,
        )

        # Convert to list of dicts
        results = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                {
                    "id": hit.id,
                    "score": hit.score,
                    "url": payload.get("url", ""),
                    "title": payload.get("title", ""),
                    "section_heading": payload.get("section_heading"),
                    "text": payload.get("text", ""),
                    "char_start": payload.get("char_start", 0),
                    "char_end": payload.get("char_end", 0),
                    "content_type": payload.get("content_type", "html"),
                    "crawl_ts": payload.get("crawl_ts", ""),
                    "last_modified": payload.get("last_modified"),
                    "embedding_model": payload.get("embedding_model", ""),
                }
            )

        logger.info(f"Retrieved {len(results)} chunks (cutoff={cutoff})")
        return results

    except Exception as e:
        logger.error(f"Error retrieving chunks: {e}")
        return []


def retrieve_with_cutoff(
    client: QdrantClient,
    collection: str,
    query_vec: np.ndarray,
    top_k: int = None,
    cutoff: float = None,
    filters: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    """Retrieve chunks with similarity cutoff applied."""
    if top_k is None:
        top_k = settings.top_k
    if cutoff is None:
        cutoff = settings.similarity_cutoff

    # First retrieve more candidates
    candidates = retrieve(client, collection, query_vec, top_k=top_k * 2, cutoff=0.0, filters=filters)

    # Apply cutoff
    filtered = [c for c in candidates if c["score"] >= cutoff]

    # Limit to top_k
    filtered = filtered[:top_k]

    return filtered



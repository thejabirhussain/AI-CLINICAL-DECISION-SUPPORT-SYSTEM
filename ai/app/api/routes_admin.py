"""Admin API routes."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Header

from app.api.deps import qdrant_client
from app.core.config import settings
from app.core.schemas import AdminStats, ReindexRequest
from app.core.security import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats", response_model=AdminStats)
async def get_stats(
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """Get collection statistics."""
    try:
        # Verify API key
        await verify_api_key(x_api_key)

        # Get collection info
        from app.vector.qdrant_client import get_collection_info

        info = get_collection_info(qdrant_client, settings.collection_name)

        stats = AdminStats(
            collection_name=settings.collection_name,
            total_chunks=info.get("points_count", 0),
            last_updated=datetime.utcnow(),  # Would get from actual collection metadata
            embedding_model=settings.openai_embed_model if settings.embeddings_provider == "openai" else "local",
            vector_size=info.get("vector_size", 0),
        )

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/reindex")
async def reindex(
    request: ReindexRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """Trigger reindexing of collection."""
    try:
        # Verify API key
        await verify_api_key(x_api_key)

        # This would trigger the reindex script
        # For now, just return success
        logger.info(f"Reindex requested (force={request.force})")

        return {"status": "accepted", "message": "Reindex job queued"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering reindex: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/ingest")
async def trigger_ingest(
    x_api_key: str = Header(..., alias="X-API-Key"),
    max_pages: int = 1000,
    concurrency: int = 4,
):
    """Trigger ingestion pipeline."""
    try:
        # Verify API key
        await verify_api_key(x_api_key)

        # This would trigger the ingestion script
        # For now, just return success
        logger.info(f"Ingest requested: max_pages={max_pages}, concurrency={concurrency}")

        return {
            "status": "accepted",
            "message": "Ingestion job queued",
            "max_pages": max_pages,
            "concurrency": concurrency,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering ingest: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

@router.post("/ingest_parquet")
async def ingest_parquet(
    x_api_key: str = Header(..., alias="X-API-Key"),
):
    """Trigger ingestion pipeline from parquet file."""
    try:
        # Verify API key
        await verify_api_key(x_api_key)

        import app.scripts.ingest_parquet as ingest_script
        ingest_script.main()

        return {
            "status": "success",
            "message": "Ingestion completed successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering ingest_parquet: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


"""RAG pipeline orchestration."""

import logging
from typing import Any, Optional

import numpy as np
from qdrant_client import QdrantClient

from app.core.config import settings
from app.core.constants import NO_KB_MSG
from app.core.prompts import build_no_results_prompt, build_rag_prompt
from app.core.security import should_add_disclaimer
from app.core.utils import estimate_tokens
from app.generation.llm import get_llm_provider
from app.generation.response_sizer import classify_query, select_response_policy
from app.vector.embeddings import get_embedding_provider
from app.vector.qdrant_client import get_client
from app.vector.reranker import get_reranker
from app.vector.retriever import retrieve_with_cutoff

logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG pipeline for question answering."""

    def __init__(self):
        self.embedding_provider = get_embedding_provider()
        self.llm_provider = get_llm_provider()
        self.qdrant_client = get_client()
        self.reranker = get_reranker()
        self.collection_name = settings.collection_name

    def answer(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None,
        top_k: Optional[int] = None,
        top_n: Optional[int] = None,
        cutoff: Optional[float] = None,
    ) -> dict[str, Any]:
        """Answer a query using RAG pipeline."""
        try:
            cls = classify_query(query)
            policy = cls["policy"]
            # Terminal logging of classification
            logger.info("[QUERY CLASSIFICATION] → %s", cls.get("type"))
            logger.info('[QUERY CONTENT] → "%s"', query)
            logger.info("[RESPONSE MODE] → %s", cls.get("response_mode"))
            # Step 1: Embed query
            query_embedding = self.embedding_provider.get_embedding(query)
            # Step 2: Retrieve chunks
            top_k = top_k or settings.top_k
            top_n = top_n or policy.top_n
            cutoff = cutoff or settings.similarity_cutoff

            chunks = retrieve_with_cutoff(
                self.qdrant_client,
                self.collection_name,
                query_embedding,
                top_k=top_k,
                cutoff=cutoff,
                filters=filters,
            )

            if not chunks:
                logger.warning(f"No chunks found for query: {query}")
                return {
                    "answer_text": NO_KB_MSG,
                    "sources": [],
                    "confidence": "low",
                    "query_embedding_similarity": [],
                    "response_level": policy.level,
                    "response_policy": {"max_tokens": policy.max_tokens, "top_n": policy.top_n},
                    "classification_type": cls.get("type"),
                    "response_mode": cls.get("response_mode"),
                }

            # Step 3: Optional reranking
            if self.reranker and len(chunks) > top_n:
                chunks = self.reranker.rerank(query, chunks, top_n=top_n)
            else:
                chunks = chunks[:top_n]

            # Step 4: Build prompt
            prompt = build_rag_prompt(chunks, query)

            # Step 5: Generate answer
            system_prompt = (
                "You are a factual assistant that answers only from the provided IRS.gov knowledge snippets. "
                f"Follow this response style: {policy.style_instruction}"
            )
            answer_text = self.llm_provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.0,
                max_tokens=policy.max_tokens,
            )

            # Step 6: Add disclaimer if needed
            if should_add_disclaimer(query):
                answer_text = f"{settings.legal_disclaimer}\n\n{answer_text}"

            # Step 7: Format sources
            sources = []
            similarities = []
            for chunk in chunks:
                sources.append(
                    {
                        "url": chunk.get("url", ""),
                        "title": chunk.get("title", ""),
                        "section": chunk.get("section_heading"),
                        "snippet": chunk.get("text", "")[:300],
                        "char_start": chunk.get("char_start", 0),
                        "char_end": chunk.get("char_end", 0),
                        "score": chunk.get("score", 0.0),
                    }
                )
                similarities.append(chunk.get("score", 0.0))

            # Step 8: Determine confidence
            avg_similarity = np.mean(similarities) if similarities else 0.0
            if avg_similarity >= 0.8:
                confidence = "high"
            elif avg_similarity >= 0.5:
                confidence = "medium"
            else:
                confidence = "low"

            return {
                "answer_text": answer_text,
                "sources": sources,
                "confidence": confidence,
                "query_embedding_similarity": similarities,
                "response_level": policy.level,
                "response_policy": {"max_tokens": policy.max_tokens, "top_n": policy.top_n},
                "classification_type": cls.get("type"),
                "response_mode": cls.get("response_mode"),
            }

        except Exception as e:
            logger.error(f"Error in RAG pipeline: {e}", exc_info=True)
            return {
                "answer_text": NO_KB_MSG,
                "sources": [],
                "confidence": "low",
                "query_embedding_similarity": [],
                "response_level": "simple",
                "response_policy": {"max_tokens": 250, "top_n": 2},
            }


def get_rag_pipeline() -> RAGPipeline:
    """Get RAG pipeline instance."""
    return RAGPipeline()


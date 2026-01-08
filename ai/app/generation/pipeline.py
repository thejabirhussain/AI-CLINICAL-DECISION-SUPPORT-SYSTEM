"""RAG pipeline orchestration."""

import logging
import re
from typing import Any, Optional

import numpy as np
from qdrant_client import QdrantClient

from app.core.config import settings
from app.core.constants import NO_KB_MSG
from app.core.prompts import build_no_results_prompt, build_rag_prompt
from app.core.security import should_add_disclaimer
from app.core.utils import estimate_tokens
from app.generation.llm import get_llm_provider
from app.generation.query_rewriter import rewrite_query
from app.generation.response_sizer import classify_query, select_response_policy
from app.vector.embeddings import get_embedding_provider
from app.vector.qdrant_client import get_client
from app.vector.reranker import get_reranker
from app.vector.optimized_reranker import get_parallel_reranker
from app.vector.retriever import retrieve_with_cutoff

logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG pipeline for question answering."""

    def __init__(self):
        self.embedding_provider = get_embedding_provider()
        self.llm_provider = get_llm_provider()
        self.qdrant_client = get_client()
        self.reranker = get_reranker()
        # Optionally wrap reranker with parallel processing for speedup
        if self.reranker:
            try:
                self.reranker = get_parallel_reranker(self.reranker, batch_size=8, max_workers=3)
            except Exception:
                pass
        self.collection_name = settings.collection_name

    def answer(
        self,
        query: str,
        filters: Optional[dict[str, Any]] = None,
        top_k: Optional[int] = None,
        top_n: Optional[int] = None,
        cutoff: Optional[float] = None,
        history: Optional[list[dict[str, str]]] = None,
        context: Optional[str] = None,
    ) -> dict[str, Any]:
        """Answer a query using RAG pipeline."""
        try:
            # Inject patient context into query if present
            # Inject patient context into query if present
            # original_query = query
            # We no longer prepend context to query to avoid confusing the classifier/embedder
            
            # Step 0: Rewrite Query for Conversational Chaining
            rewritten_query = rewrite_query(query, history)
            # Use rewritten query for classification and retrieval
            query_for_retrieval = rewritten_query
            
            cls = classify_query(query_for_retrieval)
            policy = cls["policy"]
            # Terminal logging of classification
            logger.info("[QUERY CLASSIFICATION] → %s", cls.get("type"))
            logger.info('[QUERY CONTENT] → "%s"', query_for_retrieval)
            logger.info("[RESPONSE MODE] → %s", cls.get("response_mode"))
            # Step 1: Embed query
            query_embedding = self.embedding_provider.get_embedding(query_for_retrieval) # Use rewritten query for retrieval
            
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
                logger.warning(f"No chunks found for query: {query_for_retrieval}")
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
                chunks = self.reranker.rerank(query_for_retrieval, chunks, top_n=top_n)
            else:
                chunks = chunks[:top_n]

            # Step 4: Build rolling conversation summary if history is long
            summary_text: Optional[str] = None
            if history and len(history) > 6:
                try:
                    summary_prompt = (
                        "Summarize the following chat turns into 3-6 compact bullet points capturing the main topic, entities, and clinical context. "
                        "Keep under 1200 characters. Use plain text bullets only.\n\n" +
                        "\n".join([f"{t.get('role', 'user')}: {t.get('content','')}" for t in history[-12:]])
                    )
                    summary_text = self.llm_provider.generate(
                        prompt=summary_prompt,
                        system_prompt=(
                            "You are a careful summarizer. Produce a concise, reference-friendly summary."
                        ),
                        temperature=0.0,
                        max_tokens=200,
                    )
                except Exception:
                    summary_text = None

            # Step 5: Build prompt (Use the modified query with context here so the LLM sees it)
            prompt = build_rag_prompt(chunks, query_for_retrieval, history=history, summary=summary_text, patient_context=context)

            # Step 6: Generate answer
            system_prompt = (
                "You are a Clinical Decision Support Assistant. Provide accurate, evidence-based answers. "
                f"Follow this response style: {policy.style_instruction}"
            )
            answer_text = self.llm_provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.0,
                max_tokens=policy.max_tokens,
            )

            # Step 7: Add disclaimer if needed
            if should_add_disclaimer(query):
                answer_text = f"{settings.legal_disclaimer}\n\n{answer_text}"

            # Step 7b: Strip any model-inserted Sources section to avoid duplication in UI
            def _strip_sources_sections(text: str) -> str:
                patterns = [
                    r"\n+###\s*Sources[\s\S]*$",
                    r"\n+##\s*Sources[\s\S]*$",
                    r"\n+Sources:?[\s\S]*$",
                ]
                for p in patterns:
                    text = re.sub(p, "", text, flags=re.IGNORECASE)
                return text.strip()

            answer_text = _strip_sources_sections(answer_text)

            # Step 8: Format sources
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

            # Deduplicate sources by (url, char range) keeping highest score
            unique: dict[tuple[str, int, int], dict[str, Any]] = {}
            for s in sources:
                key = (s.get("url", ""), int(s.get("char_start", 0)), int(s.get("char_end", 0)))
                if key not in unique or s.get("score", 0.0) > unique[key].get("score", 0.0):
                    unique[key] = s
            sources = list(unique.values())

            # Step 9: Determine confidence
            avg_similarity = np.mean(similarities) if similarities else 0.0
            if avg_similarity >= 0.8:
                confidence = "high"
            elif avg_similarity >= 0.5:
                confidence = "medium"
            else:
                confidence = "low"

            # Step 10: Generate follow-up questions (lightweight prompt)
            follow_up_questions: list[str] = []
            try:
                fu_prompt = (
                    "Given the user's question and the assistant's answer, suggest 3-5 short, "
                    "clickable follow-up questions that are directly relevant. Keep each under 80 characters. "
                    "Return as a JSON array of strings only.\n\n"
                    f"Question: {query}\n\nAnswer: {answer_text}\n"
                )
                fu_text = self.llm_provider.generate(
                    prompt=fu_prompt,
                    system_prompt=(
                        "You generate helpful, on-topic follow-up questions. Respond ONLY with a JSON array."
                    ),
                    temperature=0.2,
                    max_tokens=128,
                )
                # Simple JSON-safe parsing without adding deps
                import json

                parsed = json.loads(fu_text.strip())
                if isinstance(parsed, list):
                    follow_up_questions = [str(x) for x in parsed if isinstance(x, str)][:5]
            except Exception:
                follow_up_questions = []

            return {
                "answer_text": answer_text,
                "sources": sources,
                "confidence": confidence,
                "query_embedding_similarity": similarities,
                "follow_up_questions": follow_up_questions,
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
                "follow_up_questions": [],
                "response_level": "simple",
                "response_policy": {"max_tokens": 250, "top_n": 2},
            }


def get_rag_pipeline() -> RAGPipeline:
    """Get RAG pipeline instance."""
    return RAGPipeline()


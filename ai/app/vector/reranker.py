"""Cross-encoder reranking for improved retrieval."""

import logging
import math
from typing import Any, Optional

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Cross-encoder reranker using transformers."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading reranker model: {model_name} on {self.device}")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            logger.info(f"Reranker loaded successfully")
        except Exception as e:
            logger.error(f"Error loading reranker model: {e}")
            self.model = None
            self.tokenizer = None

    def rerank(
        self, query: str, chunks: list[dict[str, Any]], top_n: int = 3
    ) -> list[dict[str, Any]]:
        """Rerank chunks using cross-encoder."""
        if not self.model or not self.tokenizer:
            logger.warning("Reranker not available, returning original chunks")
            return chunks[:top_n]

        try:
            # Prepare pairs
            pairs = [(query, chunk.get("text", "")) for chunk in chunks]

            # Get scores
            with torch.no_grad():
                inputs = self.tokenizer(
                    pairs,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                ).to(self.device)

                scores = self.model(**inputs).logits.squeeze().cpu().tolist()

            # Sort by score
            scored_chunks = list(zip(chunks, scores))
            scored_chunks.sort(key=lambda x: x[1], reverse=True)

            # Update scores in chunks
            reranked = []
            for chunk, score in scored_chunks[:top_n]:
                chunk["rerank_score"] = float(score)
                chunk["score"] = 1.0 / (1.0 + math.exp(-float(score)))  # logit -> 0-1 relevance
                reranked.append(chunk)

            logger.info(f"Reranked {len(chunks)} chunks to top {top_n}")
            return reranked

        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            return chunks[:top_n]


def get_reranker(model_name: Optional[str] = None) -> Optional[CrossEncoderReranker]:
    """Get reranker instance."""
    if model_name is None:
        model_name = "cross-encoder/ms-marco-MiniLM-L-12-v2"

    try:
        return CrossEncoderReranker(model_name)
    except Exception as e:
        logger.warning(f"Could not initialize reranker: {e}")
        return None



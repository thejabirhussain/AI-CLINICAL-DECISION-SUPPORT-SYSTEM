"""Optimized cross-encoder reranking with parallel batch processing."""

import logging
import math
from typing import Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import torch

logger = logging.getLogger(__name__)


class ParallelCrossEncoderReranker:
    """
    Parallel reranker that processes chunks in batches using ThreadPoolExecutor.
    
    This is a wrapper around the original CrossEncoderReranker that adds
    parallel processing for 2-3x speedup on large chunk sets.
    """
    
    def __init__(self, original_reranker, batch_size: int = 8, max_workers: int = 3):
        """
        Initialize parallel reranker wrapper.
        
        Args:
            original_reranker: Instance of CrossEncoderReranker
            batch_size: Number of chunks to process in each parallel batch
            max_workers: Number of parallel threads to use
        """
        self.reranker = original_reranker
        self.batch_size = batch_size
        self.max_workers = max_workers
        logger.info(f"ParallelReranker initialized: batch_size={batch_size}, workers={max_workers}")
    
    def rerank(
        self, query: str, chunks: List[dict[str, Any]], top_n: int = 3
    ) -> List[dict[str, Any]]:
        """
        Rerank chunks using parallel batch processing.
        
        Args:
            query: User query string
            chunks: List of chunk dictionaries to rerank
            top_n: Number of top chunks to return
        
        Returns:
            List of top_n reranked chunks with scores
        """
        if not getattr(self.reranker, "model", None) or not getattr(self.reranker, "tokenizer", None):
            logger.warning("Reranker not available, returning original chunks")
            return chunks[:top_n]
        
        # If chunks are few, no need for parallelization overhead
        if len(chunks) <= self.batch_size:
            logger.debug(f"Small batch ({len(chunks)} chunks), using sequential reranking")
            return self.reranker.rerank(query, chunks, top_n)
        
        try:
            # Split chunks into batches
            batches = [
                chunks[i:i + self.batch_size] 
                for i in range(0, len(chunks), self.batch_size)
            ]
            logger.info(f"Processing {len(chunks)} chunks in {len(batches)} parallel batches")
            
            # Process batches in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all batches for processing
                future_to_batch = {
                    executor.submit(self._score_batch, query, batch, batch_idx): batch_idx
                    for batch_idx, batch in enumerate(batches)
                }
                
                # Collect results as they complete
                all_scored_chunks = []
                for future in as_completed(future_to_batch):
                    batch_idx = future_to_batch[future]
                    try:
                        scored_batch = future.result()
                        all_scored_chunks.extend(scored_batch)
                    except Exception as e:
                        logger.error(f"Error processing batch {batch_idx}: {e}")
            
            # Sort all chunks by rerank score
            all_scored_chunks.sort(key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            
            # Return top N
            reranked = all_scored_chunks[:top_n]
            logger.info(f"Parallel reranking complete: {len(chunks)} → {len(reranked)} chunks")
            
            return reranked
        
        except Exception as e:
            logger.error(f"Error in parallel reranking: {e}, falling back to sequential")
            return self.reranker.rerank(query, chunks, top_n)
    
    def _score_batch(
        self, query: str, batch: List[dict[str, Any]], batch_idx: int
    ) -> List[dict[str, Any]]:
        """
        Score a single batch of chunks (runs in parallel thread).
        
        Args:
            query: User query
            batch: List of chunks in this batch
            batch_idx: Index of this batch (for logging)
        
        Returns:
            List of chunks with rerank_score added
        """
        try:
            # Prepare query-text pairs for this batch
            pairs = [(query, chunk.get("text", "")) for chunk in batch]
            
            # Tokenize and score using the model
            with torch.no_grad():
                inputs = self.reranker.tokenizer(
                    pairs,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                ).to(self.reranker.device)
                
                # Get scores from model
                scores = self.reranker.model(**inputs).logits.squeeze()
                
                # Handle single-item batch (scores would be 0-d tensor)
                if scores.dim() == 0:
                    scores = [scores.item()]
                else:
                    scores = scores.cpu().tolist()
            
            # Attach scores to chunks
            for chunk, score in zip(batch, scores):
                chunk["rerank_score"] = float(score)
                chunk["score"] = 1.0 / (1.0 + math.exp(-float(score)))  # logit -> 0-1 relevance
            
            logger.debug(f"Batch {batch_idx}: scored {len(batch)} chunks")
            return batch
        
        except Exception as e:
            logger.error(f"Error scoring batch {batch_idx}: {e}")
            # Return chunks with default scores on error
            for chunk in batch:
                chunk["rerank_score"] = 0.0
            return batch


def get_parallel_reranker(original_reranker, batch_size: int = 8, max_workers: int = 3):
    """
    Wrap original reranker with parallel processing.
    
    Args:
        original_reranker: Instance of CrossEncoderReranker
        batch_size: Chunks per batch (8 works well for most systems)
        max_workers: Number of parallel threads (3 is safe for most CPUs)
    
    Returns:
        ParallelCrossEncoderReranker instance
    """
    if original_reranker is None:
        return None
    return ParallelCrossEncoderReranker(original_reranker, batch_size, max_workers)

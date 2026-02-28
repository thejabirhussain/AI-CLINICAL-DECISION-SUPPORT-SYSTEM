"""Ingest MedQuAD dataset from a local Parquet file into Qdrant."""

import urllib.request
urllib.request.getproxies = lambda: {}

import logging
from datetime import datetime, timezone
import uuid
import sys

import pandas as pd
from tqdm import tqdm

from app.core.config import settings
from app.core.logging import setup_logging
from app.vector.embeddings import get_embedding_provider
from app.vector.qdrant_client import ensure_collection, get_client as get_qdrant_client
from qdrant_client.models import PointStruct

setup_logging()
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting ingestion from data.parquet")
    try:
        df = pd.read_parquet("data.parquet")
        logger.info(f"Loaded {len(df)} records from data.parquet")
    except Exception as e:
        logger.error(f"Failed to read parquet: {e}")
        sys.exit(1)
        
    limit = 11000
    if len(df) > limit:
        df = df.iloc[:limit]
        
    client = get_qdrant_client()
    embedding_provider = get_embedding_provider()
    ensure_collection(client, settings.collection_name, embedding_provider.vector_size)
    
    total_upserted = 0
    points = []
    batch_texts = []
    batch_metadata = []
    batch_size = 200
    
    # keivalya/MedQuad-MedicalQnADataset has 'qtype', 'Question', 'Answer'
    for i, row in tqdm(df.iterrows(), total=len(df), desc="Processing"):
        qtype = str(row.get("qtype", "General") or "General")
        question = str(row.get("Question", ""))
        answer = str(row.get("Answer", ""))
        
        if not question or not answer or pd.isna(question) or pd.isna(answer):
            continue
            
        text = f"Question: {question}\nAnswer: {answer}"
        batch_texts.append(text)
        
        metadata = {
            "url": f"local://MedQuAD/{i}",
            "title": f"MedQuAD QA: {qtype}",
            "section_heading": qtype,
            "char_start": 0,
            "char_end": len(text),
            "content_type": "qa_pair",
            "crawl_ts": datetime.now(timezone.utc).isoformat(),
            "language": "en",
            "source_type": "medical_qa_dataset",
            "filename": "data.parquet"
        }
        batch_metadata.append(metadata)
        
        if len(batch_texts) >= batch_size:
            try:
                embeddings = embedding_provider.get_embeddings(batch_texts)
                for tex, emb, meta in zip(batch_texts, embeddings, batch_metadata):
                    meta["text"] = tex
                    points.append(PointStruct(
                        id=str(uuid.uuid4()),
                        vector=emb.tolist(),
                        payload=meta
                    ))
                client.upsert(collection_name=settings.collection_name, points=points)
                total_upserted += len(points)
            except Exception as e:
                logger.error(f"Error in batch: {e}")
                
            points = []
            batch_texts = []
            batch_metadata = []
            
    # Process remaining
    if batch_texts:
        try:
            embeddings = embedding_provider.get_embeddings(batch_texts)
            for tex, emb, meta in zip(batch_texts, embeddings, batch_metadata):
                meta["text"] = tex
                points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=emb.tolist(),
                    payload=meta
                ))
            client.upsert(collection_name=settings.collection_name, points=points)
            total_upserted += len(points)
        except Exception as e:
            logger.error(f"Error in final batch: {e}")
            
    logger.info(f"Ingestion complete. Total chunks upserted: {total_upserted}")

if __name__ == "__main__":
    main()

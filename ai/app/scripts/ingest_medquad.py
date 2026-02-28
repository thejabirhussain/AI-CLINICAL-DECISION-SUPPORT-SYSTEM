"""Ingest HuggingFace MedQuAD dataset into Qdrant."""

import logging
from datetime import datetime, timezone
import uuid

import typer
from tqdm import tqdm

from app.core.config import settings
from app.core.logging import setup_logging
from app.vector.embeddings import get_embedding_provider
from app.vector.qdrant_client import ensure_collection, get_client as get_qdrant_client
from qdrant_client.models import PointStruct
from datasets import load_dataset

setup_logging()
logger = logging.getLogger(__name__)

app = typer.Typer()

@app.command()
def main(
    collection_name: str = typer.Option(settings.collection_name, help="Qdrant collection name"),
    limit: int = typer.Option(11000, help="Number of records to ingest to reach 10,000+ points"),
    batch_size: int = typer.Option(200, help="Batch size for upserting")
):
    """Ingest MedQuAD dataset from HuggingFace into Qdrant."""
    logger.info("Loading MedQuAD dataset from HuggingFace...")
    # keivalya/MedQuad-MedicalQnADataset has 'qtype', 'Question', 'Answer'
    dataset = load_dataset("keivalya/MedQuad-MedicalQnADataset", split='train')
    
    # Take a subset if limit is specified
    if limit:
        dataset = dataset.select(range(min(limit, len(dataset))))
        
    logger.info(f"Loaded {len(dataset)} records. Setting up Qdrant...")
    
    client = get_qdrant_client()
    embedding_provider = get_embedding_provider()
    ensure_collection(client, collection_name, embedding_provider.vector_size)
    
    total_upserted = 0
    points = []
    
    # Batch texts for faster embedding
    batch_texts = []
    batch_metadata = []
    
    for i, row in enumerate(tqdm(dataset, desc="Processing and Embedding")):
        qtype = row.get("qtype", "General") if row.get("qtype") else "General"
        question = row.get("Question", "")
        answer = row.get("Answer", "")
        
        if not question or not answer:
            continue
            
        text = f"Question: {question}\nAnswer: {answer}"
        batch_texts.append(text)
        
        metadata = {
            "url": f"hf://MedQuAD/{i}",
            "title": f"MedQuAD QA: {qtype}",
            "section_heading": qtype,
            "char_start": 0,
            "char_end": len(text),
            "content_type": "qa_pair",
            "crawl_ts": datetime.now(timezone.utc).isoformat(),
            "language": "en",
            "source_type": "medical_qa_dataset",
            "filename": "MedQuAD"
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
                client.upsert(collection_name=collection_name, points=points)
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
            client.upsert(collection_name=collection_name, points=points)
            total_upserted += len(points)
        except Exception as e:
            logger.error(f"Error in final batch: {e}")
        
    logger.info(f"Ingestion complete. Total chunks upserted: {total_upserted}")

if __name__ == "__main__":
    app()

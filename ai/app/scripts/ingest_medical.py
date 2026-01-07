"""Medical Guideline Ingestion Script."""

import glob
import logging
import os
from pathlib import Path
from datetime import datetime, timezone

import typer
from tqdm import tqdm

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.utils import compute_content_hash
from app.ingestion.chunker import chunk_page
from app.ingestion.models import CrawledPage, ContentType
from app.ingestion.parse_pdf import extract_pdf_text
from app.vector.embeddings import get_embedding_provider
from app.vector.qdrant_client import ensure_collection, get_client
from app.vector.qdrant_client import get_client as get_qdrant_client

setup_logging()
logger = logging.getLogger(__name__)

app = typer.Typer()

def ingest_file(file_path: Path, collection_name: str, embedding_provider):
    """Ingest a single local PDF file."""
    try:
        logger.info(f"Processing {file_path.name}...")
        
        # Read file
        content = file_path.read_bytes()
        
        # Parse based on type
        if file_path.suffix.lower() == ".pdf":
            text, metadata = extract_pdf_text(content)
            c_type = ContentType.PDF
        else:
            # Assume text
            text = content.decode("utf-8", errors="ignore")
            metadata = {}
            c_type = ContentType.HTML  # Fallback type or new type if available
        
        if not text:
            logger.warning(f"No text extracted from {file_path.name}")
            return 0
            
        # Create Page Object
        page = CrawledPage(
            url=f"http://local/{file_path.name}", # Hack to satisfy detailed validation
            title=file_path.stem.replace("_", " ").title(),
            raw_content=content,
            cleaned_text=text,
            content_type=c_type,
            content_hash=compute_content_hash(content),
            crawl_timestamp=datetime.now(timezone.utc)
        )
        
        # Chunk
        chunks = chunk_page(page)
        if not chunks:
            logger.warning(f"No chunks created for {file_path.name}")
            return 0

        # Embed
        chunk_texts = [chunk.chunk_text for chunk in chunks]
        embeddings = embedding_provider.get_embeddings(chunk_texts)
        
        # Upsert
        client = get_qdrant_client()
        from qdrant_client.models import PointStruct
        
        points = []
        for chunk, embedding in zip(chunks, embeddings):
            points.append(PointStruct(
                id=chunk.chunk_id,
                vector=embedding.tolist(),
                payload={
                    "url": str(chunk.page_url),
                    "title": page.title,
                    "section_heading": chunk.section_heading,
                    "text": chunk.chunk_text,
                    "char_start": chunk.char_offset_start,
                    "char_end": chunk.char_offset_end,
                    "content_type": "pdf",
                    "crawl_ts": chunk.crawl_timestamp.isoformat(),
                    "language": "en",
                    "source_type": "medical_guideline",
                    "filename": file_path.name
                }
            ))
            
        client.upsert(collection_name=collection_name, points=points)
        logger.info(f"Upserted {len(points)} chunks from {file_path.name}")
        return len(points)
        
    except Exception as e:
        logger.error(f"Failed to ingest {file_path}: {e}")
        return 0

@app.command()
def main(
    directory: str = typer.Option("./data/medical_docs", help="Directory containing guidelines"),
    collection_name: str = typer.Option(settings.collection_name, help="Qdrant collection name"),
    pattern: str = typer.Option("*.*", help="File pattern to match"),
):
    """Ingest local medical documents (PDF/TXT) into Qdrant."""
    input_dir = Path(directory)
    if not input_dir.exists():
        logger.error(f"Directory {directory} does not exist.")
        return

    # Find files (pdf and txt)
    files = [f for f in input_dir.glob(pattern) if f.suffix.lower() in ('.pdf', '.txt')]
    logger.info(f"Found {len(files)} files in {directory}")

    # Setup
    client = get_qdrant_client()
    embedding_provider = get_embedding_provider()
    ensure_collection(client, collection_name, embedding_provider.vector_size)

    total_chunks = 0
    with tqdm(total=len(files), desc="Ingesting Files") as pbar:
        for file_path in files:
            chunks = ingest_file(file_path, collection_name, embedding_provider)
            total_chunks += chunks
            pbar.update(1)

    logger.info(f"Ingestion complete. Total chunks: {total_chunks}")

if __name__ == "__main__":
    app()

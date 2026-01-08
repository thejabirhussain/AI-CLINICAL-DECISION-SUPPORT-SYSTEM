"""Medical Web Ingestion Script."""

import asyncio
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Iterable
from pathlib import Path
from urllib.parse import urlparse

import typer
from tqdm import tqdm
from bs4 import BeautifulSoup
import httpx

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.utils import compute_content_hash
from app.ingestion.chunker import chunk_page
from app.ingestion.crawler import create_crawler
from app.ingestion.parse_html import parse_html
from app.ingestion.parse_pdf import parse_pdf
from app.ingestion.sitemap import get_seed_urls
from app.ingestion.storage import StorageManager
from app.vector.embeddings import get_embedding_provider
from app.vector.qdrant_client import ensure_collection, get_client
from app.vector.qdrant_client import get_client as get_qdrant_client

setup_logging()
logger = logging.getLogger(__name__)

app = typer.Typer()


def _is_pdf_url(url: str) -> bool:
    return url.lower().endswith(".pdf")


def _filter_by_prefix(urls: Iterable[str], allow_prefix: list[str] | None, block_prefix: list[str] | None) -> list[str]:
    def allowed(u: str) -> bool:
        path = urlparse(u).path or "/"
        if block_prefix:
            for bp in block_prefix:
                if path.startswith(bp):
                    return False
        if allow_prefix:
            for ap in allow_prefix:
                if path.startswith(ap):
                    return True
            return False
        return True

    return [u for u in urls if allowed(u)]


def _read_url_file(url_file: Optional[str]) -> list[str]:
    if not url_file:
        return []
    p = Path(url_file)
    if not p.exists():
        logger.warning(f"URL file not found: {url_file}")
        return []
    out: list[str] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    return out


def _discover_links_from_seed(seed_url: str, allow_prefixes: list[str] | None, limit: int) -> list[str]:
    """Fetch the seed page and collect same-domain links, optionally filtered by path prefixes."""
    out: list[str] = []
    try:
        resp = httpx.get(seed_url, timeout=30.0, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        base = f"{urlparse(seed_url).scheme}://{urlparse(seed_url).netloc}"
        for a in soup.find_all("a"):
            href = a.get("href")
            if not href:
                continue
            if href.startswith("#"):
                continue
            # Join relative links
            if href.startswith("/"):
                url = f"{base}{href}"
            elif href.startswith("http://") or href.startswith("https://"):
                url = href
            else:
                # Skip non-http(s) schemes
                continue
            # Same domain
            if urlparse(url).netloc != urlparse(seed_url).netloc:
                continue
            path = urlparse(url).path or "/"
            if allow_prefixes:
                if not any(path.startswith(p) for p in allow_prefixes):
                    continue
            out.append(url)
            if len(out) >= limit:
                break
    except Exception as e:
        logger.debug(f"Seed link discovery failed for {seed_url}: {e}")
    return out


def upsert_chunks_to_qdrant(chunks: list, embeddings: list, collection_name: str):
    """Upsert chunks to Qdrant."""
    client = get_qdrant_client()
    from datetime import datetime
    from qdrant_client.models import PointStruct

    points = []
    for chunk, embedding in zip(chunks, embeddings):
        point = PointStruct(
            id=chunk.chunk_id,
            vector=embedding.tolist(),
            payload={
                "url": str(chunk.page_url),
                "title": chunk.chunk_text[:100] if chunk.chunk_text else "",  # Simplified
                "section_heading": chunk.section_heading,
                "text": chunk.chunk_text,
                "char_start": chunk.char_offset_start,
                "char_end": chunk.char_offset_end,
                "content_type": chunk.content_type.value,
                "crawl_ts": chunk.crawl_timestamp.isoformat(),
                "language": "en",
                "embedding_model": settings.openai_embed_model if settings.embeddings_provider == "openai" else "local",
                "tokens": len(chunk.chunk_text) // 4,
                "hash": compute_content_hash(chunk.chunk_text),
                "source_type": "web_crawl"
            },
        )
        points.append(point)

    # Batch upsert
    client.upsert(collection_name=collection_name, points=points)
    logger.info(f"Upserted {len(points)} chunks to Qdrant")


def process_page(url: str, crawler, storage: StorageManager, collection_name: str):
    """Process a single page: crawl, parse, chunk, embed, upsert."""
    try:
        # Crawl
        page = crawler.fetch(url)
        if not page:
            return None

        # Compute hash
        page.content_hash = compute_content_hash(page.raw_content)

        # Save raw
        storage.save_raw_page(page)

        # Parse
        if page.content_type.value == "pdf":
            page = parse_pdf(page)
        else:
            page = parse_html(page)

        # Save cleaned
        storage.save_cleaned_page(page)

        # Chunk
        chunks = chunk_page(page)
        if not chunks:
            return None

        # Save chunks
        storage.save_chunks(chunks, str(page.url))

        # Embed
        embedding_provider = get_embedding_provider()
        chunk_texts = [chunk.chunk_text for chunk in chunks]
        embeddings = embedding_provider.get_embeddings(chunk_texts)

        # Upsert to Qdrant
        upsert_chunks_to_qdrant(chunks, embeddings, collection_name)

        return len(chunks)

    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        return None


@app.command()
def main(
    seed: str = typer.Option("https://www.ncbi.nlm.nih.gov/books/", help="Seed URL to start crawling (e.g., NCBI Bookshelf)"),
    max_pages: int = typer.Option(500, help="Maximum number of pages to crawl"),
    concurrency: int = typer.Option(4, help="Number of concurrent workers"),
    allow_pdf: bool = typer.Option(True, help="Allow PDF crawling"),
    collection_name: str = typer.Option(settings.collection_name, help="Qdrant collection name"),
    url_file: Optional[str] = typer.Option(None, help="Path to a file containing URLs to ingest (one per line)"),
    allow_prefix: Optional[str] = typer.Option(None, help="Comma-separated list of path prefixes to ALLOW"),
    block_prefix: Optional[str] = typer.Option(None, help="Comma-separated list of path prefixes to BLOCK"),
    only_pdf: bool = typer.Option(False, help="If true, only process PDF URLs"),
    only_html: bool = typer.Option(False, help="If true, only process HTML URLs"),
    include_seed: bool = typer.Option(True, help="Include the seed URL itself in targets before filtering"),
    follow_links: bool = typer.Option(True, help="Shallowly collect links from the seed page"),
    ignore_robots: bool = typer.Option(False, help="Ignore robots.txt restrictions (use with caution)"),
):
    """Ingest medical content from web: crawl, parse, chunk, embed, and upsert to Qdrant."""
    logger.info(f"Starting ingestion: seed={seed}, max_pages={max_pages}, concurrency={concurrency}")

    # Setup
    crawler = create_crawler(seed, ignore_robots=ignore_robots)
    storage = StorageManager()
    client = get_qdrant_client()

    # Ensure collection exists
    embedding_provider = get_embedding_provider()
    ensure_collection(client, collection_name, embedding_provider.vector_size)

    # Build target URL set
    target_urls: list[str] = []

    # 1) URLs from file
    file_urls = _read_url_file(url_file)
    if file_urls:
        logger.info(f"Loaded {len(file_urls)} URLs from file")
        target_urls.extend(file_urls)

    # 2) Optionally include the seed URL itself
    if include_seed:
        target_urls.append(seed)

    # 3) Link discovery / Sitemap
    allow_list = [s.strip() for s in (allow_prefix.split(",") if allow_prefix else []) if s.strip()]
    block_list = [s.strip() for s in (block_prefix.split(",") if block_prefix else []) if s.strip()]
    
    if follow_links:
        logger.info(f"Discovering links from seed: {seed}")
        discovered = _discover_links_from_seed(seed, allow_list or None, limit=max_pages)
        if discovered:
            logger.info(f"Discovered {len(discovered)} links from seed page")
            target_urls.extend(discovered)
    elif "ncbi" in seed:
         # Fallback sitemap logic if suitable, but shallow crawl is safer for general medical sites
         pass

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for u in target_urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)

    # Apply allow/block prefix filters (path-based)
    filtered = _filter_by_prefix(deduped, allow_list or None, block_list or None)

    # Apply content-type pre-filtering if requested
    if only_pdf and only_html:
        logger.warning("Both only_pdf and only_html set; defaulting to process all")
    elif only_pdf:
        filtered = [u for u in filtered if _is_pdf_url(u)]
    elif only_html:
        filtered = [u for u in filtered if not _is_pdf_url(u)]
    # Honor legacy allow_pdf flag (exclude PDFs when false)
    if not allow_pdf and not only_html and not only_pdf:
        filtered = [u for u in filtered if not _is_pdf_url(u)]

    # Enforce master max_pages cap
    target_list = filtered[:max_pages]
    logger.info(f"Total target URLs after filtering: {len(target_list)}")

    # Process pages
    processed = 0
    total_chunks = 0

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(process_page, url, crawler, storage, collection_name): url for url in target_list}

        with tqdm(total=len(target_list), desc="Processing pages") as pbar:
            for future in as_completed(futures):
                url = futures[future]
                try:
                    chunks_count = future.result()
                    if chunks_count:
                        processed += 1
                        total_chunks += chunks_count
                        pbar.update(1)
                except Exception as e:
                    logger.error(f"Error processing {url}: {e}")
                    pbar.update(1)

    crawler.close()
    logger.info(f"Ingestion complete: {processed} pages, {total_chunks} chunks")


if __name__ == "__main__":
    app()

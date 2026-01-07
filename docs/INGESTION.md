# Medical Data Ingestion Guide

This CDSS platform uses a robust Qdrant-based knowledge base. The ingestion scripts are designed to be **idempotent**, meaning you can run them multiple times without duplicating data (content hashing is used for deduplication).

## 1. Environment Setup

Ensure your local environment is set up and key environment variables are present in `ai/.env`:

```bash
# ai/.env
QDRANT_HOST=qdrant
QDRANT_PORT=6333
COLLECTION_NAME=medical_docs
OPENAI_API_KEY=sk-... # If using OpenAI embeddings
# OR
EMBEDDING_PROVIDER=local # If using local HF embeddings
```

## 2. Ingesting Medical Guidelines (PDFs)

This script scans a directory for PDF files, extracts text using specialized PDF parsers (preserving layout where possible), chunks the content, and indexes it.

**Usage:**

```bash
# From the 'ai' directory
python -m app.scripts.ingest_medical \
  --directory ./data/medical_docs \
  --collection-name medical_docs
```

**Key Features:**
- **Automatic Deduplication**: Re-running the script on the same files will not create duplicate vectors.
- **Smart Chunking**: Respects section headers and page boundaries.

## 3. Ingesting Medical Websites

This script crawls trusted medical websites (like NCBI, WHO, or specific clinical guideline sites). It respects `robots.txt` (where applicable) and allows for strict path filtering to ensure only high-quality guidelines are indexed.

**Usage:**

```bash
# From the 'ai' directory

# Example: Ingest from a specific seed URL
python -m app.scripts.ingest_web \
  --seed "https://www.ncbi.nlm.nih.gov/books/NBK573325/" \
  --max-pages 100 \
  --collection-name medical_docs \
  --include-seed

# Example: Ingest a list of URLs from a file
python -m app.scripts.ingest_web \
  --url-file ./data/sources.txt \
  --max-pages 500
```

**Options:**
- `--allow-pdf / --no-allow-pdf`: Whether to crawl linked PDFs.
- `--allow-prefix`: Restrict crawling to specific sub-paths (e.g., `/guidelines/`).
- `--block-prefix`: Exclude specific sections (e.g., `/references/`, `.jpg`).

## 4. Verification

After ingestion, you can verify the data is available in the vector database.

**Check Collection Info:**

```bash
curl http://localhost:6333/collections/medical_docs
```

The `vectors_count` should reflect the number of chunks ingested.

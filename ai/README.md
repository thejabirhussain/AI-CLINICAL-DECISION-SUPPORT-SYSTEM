# Clinical Decision Support API

A production-ready Retrieval-Augmented Generation (RAG) service for Clinical Decision Support. The service provides verifiable citations for every answer from trusted medical guidelines and supports patient data analysis.

## Overview

This CDSS system:
- **Scrapes and indexes** reliable medical content (HTML and PDFs)
- **Analyzes Patient Data** from PDFs and Images (OCR)
- **Provides citations** from guidelines with section/page accuracy
- **Enforces guardrails** for clinical safety
- **Supports multiple providers** for embeddings and LLMs
- **Runs locally** with Docker Compose

## Features

- ✅ **Respectful crawling**: Follows robots.txt for medical sites
- ✅ **Multi-format support**: HTML, PDFs, and Medical Images (OCR)
- ✅ **Smart chunking**: Section-aware chunking for medical texts
- ✅ **Vector search**: Qdrant with HNSW indexing
- ✅ **Citation system**: Answers include source URL, guideline title, and section
- ✅ **Guardrails**: Clinical disclaimers and "unknown" fallbacks
- ✅ **Type safety**: Full type hints
- ✅ **Testing**: Unit and integration tests

## Tech Stack

- **Language**: Python 3.11+
- **Backend**: FastAPI
- **Vector DB**: Qdrant
- **OCR**: Tesseract + Pillow for medical images
- **Embeddings**: OpenAI or Local (`all-MiniLM-L6-v2`)
- **LLM**: GPT-4o or Ollama (`llama3`, `meditron`)
- **PDF parsing**: PyMuPDF
- **Task queue**: Async processing

## Prerequisites

- **Docker** and **Docker Compose**
- **Python 3.11+**
- **Tesseract OCR**: Required for image analysis.
  - Mac: `brew install tesseract`
  - Linux: `apt-get install tesseract-ocr`
- **OpenAI API key** (optional)
- **Ollama** (optional)

## Quickstart

### 1. Setup Environment

```bash
cd "AI-CDSS"
cp .env.example .env
# Set QDRANT_URL, API keys etc.
```

### 2. Start Services

```bash
docker-compose up -d
```

### 3. Ingest Medical Content

```bash
# Ingest local PDFs
python -m app.scripts.ingest_medical

# Ingest Web (CDC/NCBI)
python -m app.scripts.ingest_web --seed "https://www.cdc.gov/flu/" --max-pages 500
```

### 4. Start API

```bash
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Query the API

```bash
curl -X POST "http://localhost:8000/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the first-line treatments for hypertension?",
    "json": true
  }'
```

**Response:**
```json
{
  "answer_text": "First-line treatments include thiazide diuretics...",
  "sources": [
    {
      "url": "file://hypertension_guideline.pdf",
      "title": "JNC 8 Guidelines",
      ...
    }
  ],
  "confidence": "high"
}
```

## Configuration

### Environment Variables
Edit `.env` to configure:
```bash
# ...
# Crawling
CRAWL_BASE=https://www.ncbi.nlm.nih.gov/books/
RATE_LIMIT_RPS=0.5

# Legal Disclaimer
LEGAL_DISCLAIMER=I am an AI assistant; for medical advice consult a qualified physician.
```

## Evaluation
Run the evaluation suite with clinical queries:
```bash
python -m app.scripts.eval_suite --output-file eval_results.json
```

## Limitations
- **Scope**: Medical guidelines only.
- **No live web**: Answers based on indexed content.
- **No medical advice**: System provides information, not diagnosis.


## Security & Compliance

- ✅ **TLS/HTTPS**: Required in production (TLS termination at load balancer)
- ✅ **API Key Auth**: Required for admin endpoints
- ✅ **Rate Limiting**: Per-IP rate limits via `slowapi`
- ✅ **Secrets Management**: Use Azure Key Vault or AWS Secrets Manager
- ✅ **PII Masking**: Logs mask SSNs, EINs, etc.
- ✅ **Dependency Scanning**: GitHub Dependabot enabled
- ✅ **Encryption**: Qdrant at-rest encryption (if managed)

## Maintenance

### Re-crawl Schedule

Set up a cron job or scheduled task to re-crawl IRS.gov:

```bash
# Daily re-crawl (example cron)
0 2 * * * cd /path/to/project && python -m app.scripts.ingest --max-pages 1000
```

The crawler respects `If-Modified-Since` and `ETag` headers to avoid re-downloading unchanged content.

### Versioning Chunks

Chunks are versioned: never deleted, marked `is_latest=false` when obsolete. This preserves history and enables rollback.

### Backup

Export snapshots regularly:

```bash
python -m app.scripts.export_snapshot --output-dir snapshots
```

## Troubleshooting

### Qdrant Connection Issues

```bash
# Check Qdrant is running
curl http://localhost:6333/health

# Check docker-compose
docker-compose ps
docker-compose logs qdrant
```

### Embedding Issues

```bash
# Test local embeddings
python -c "from app.vector.embeddings import LocalEmbeddingProvider; p = LocalEmbeddingProvider(); print(p.get_embedding('test'))"
```

### LLM Issues

```bash
# Test Ollama
curl http://localhost:11434/api/generate -d '{"model":"llama3","prompt":"test"}'
```

## License

MIT

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run `make fmt lint typecheck test`
5. Submit a pull request

## Support

For issues and questions, please open an issue on GitHub.



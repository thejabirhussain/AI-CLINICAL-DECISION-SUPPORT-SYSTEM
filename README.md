# Clinical Decision Support System (AI-CDSS)

A minimalist RAG-based AI platform for clinical decision support.

## Features

- **Clinical Knowledge Base**: Ingests medical guidelines and journals (Qdrant).
- **Patient Context Aware**: Upload patient reports (PDF) to ground AI analysis.
- **Evidence-Based**: Answers queries using retrieved medical sources with citations.
- **Dashboard UI**: React-based clinical interface for case analysis.

## Domain Transformation
This repository was transformed from a Tax RAG system to a Medical CDSS.
- **Backend**: Python/FastAPI (`ai/`)
- **Frontend**: React/Vite (`ui/`)
- **Vector DB**: Qdrant

## Getting Started

### 1. Start Services
```bash
docker-compose up -d --build
```
(Or run individually: `make -C ai up` and `cd ui && npm run dev`)

### 2. Ingest Medical Data
Place medical PDFs in `ai/data/medical_docs` (create if needed) and run:
```bash
docker-compose exec api python -m app.scripts.ingest_medical --directory /app/data/medical_docs
```

### 3. Access UI
Open http://localhost:5173

### 4. Access API Docs
Open http://localhost:8000/docs









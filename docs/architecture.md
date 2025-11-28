# IRS RAG Application Architecture

```mermaid
flowchart LR
  %% Frontend
  subgraph FE[Frontend]
    UI[ React UI]
  end
  %% Backend API
  subgraph BE[Backend API FastAPI]
    API[FastAPI Service]
    AUTH[API Key Auth]
    RATELIMIT[Rate Limiting]
    RETRIEVER[Retriever + Reranker]
    RAG[RAG Orchestrator]
  end
  %% Vector DB
  subgraph VDB[Vector DB]
    QDRANT[Qdrant HNSW]
  end
  %% External Providers
  subgraph EXT[External Providers]
    OPENAI[(Ollama 8B)]
    OLLAMA[(Ollama 3B)]
  end
  %% Ingestion Pipeline
  subgraph ING[Ingestion Pipeline]
    CRAWL[Crawler]
    PARSE[Parsers]
    CHUNK[Chunker]
    EMBED[Embedder]
    UPSERT[Upserter]
  end
  %% Config
  subgraph CFG[Configuration]
    ENV[Environment Config]
  end
  %% Main Flows
  USER(("End User")) -->|HTTPS| UI
  UI -->|API Proxy| API
  API --> AUTH
  API --> RATELIMIT
  API --> RAG
  RAG --> RETRIEVER
  RETRIEVER -->|Vector Search| QDRANT
  RETRIEVER -->|Optional Rerank| RAG
  RAG -->|LLM Calls| OPENAI
  RAG -.->|Optional| OLLAMA
  CRAWL --> PARSE --> CHUNK --> EMBED --> UPSERT --> QDRANT
  ENV -.-> API
  ENV -.-> ING
  ENV -.-> QDRANT
  %% ============================
  %% Docker Compose Network
  %% ============================
  subgraph DC[Docker Compose Network]
    API
    QDRANT
  end
  %% Classes
  classDef svc fill:#eef7ff,stroke:#7aa7e9,color:#0a2a66;
  classDef ext fill:#fff7e6,stroke:#e7a441,color:#7a4b00;
  class API,RAG,RETRIEVER,RATELIMIT,AUTH svc;
  class OPENAI,OLLAMA ext;
```

## Notes

- **Frontend**: Vite + React dev server proxies API calls to `http://localhost:8000`.
- **Backend**: FastAPI app exposes chat endpoints (e.g., `/v1/chat`) and health checks (`/health`).
- **Vector DB**: Qdrant stores embeddings and supports similarity search (HNSW). Data persisted under `ai/infra/qdrant` when running via Docker.
- **Ingestion**: Crawler → Parser (HTML/PDF) → Chunker → Embedder → Upserter to Qdrant. Launched via `python -m app.scripts.ingest` or the provided scripts.
- **LLM/Embeddings**: Default via OpenAI; Ollama is optional for local LLM. Selection controlled by environment variables in `.env`.
- **Runtime**: Orchestrated by `docker-compose.yml` (services: `qdrant`, `api`).

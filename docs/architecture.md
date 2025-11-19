# IRS RAG Application Architecture

```mermaid
flowchart LR
  %% Frontend
  subgraph FE[Frontend]
    UI["Vite + React UI\nhttp://localhost:5173"]
  end

  %% Backend API
  subgraph BE[Backend API (FastAPI)]
    API["FastAPI Service\nuvicorn app.api.main:app\nhttp://localhost:8000"]
    RATELIMIT["Rate Limiting (slowapi)"]
    AUTH["API Key Auth"]
    RETRIEVER["Retriever + Reranker"]
    RAG["RAG Orchestrator"]
  end

  %% Vector DB
  subgraph VDB[Vector DB]
    QDRANT["Qdrant (HNSW)\n:6333 HTTP / :6334 gRPC\nPersisted to ai/infra/qdrant"]
  end

  %% External Providers
  subgraph EXT[External/Optional Providers]
    OPENAI[(OpenAI\nLLM + Embeddings)]
    OLLAMA[(Ollama\nLocal LLM)]
  end

  %% Ingestion Pipeline
  subgraph ING[Ingestion Pipeline]
    CRAWL["Crawler\n(robots-aware)"]
    PARSE["Parsers\n(HTML + PDF)"]
    CHUNK["Chunker\n(section-aware + overlap)"]
    EMBED["Embedder\n(OpenAI or local ST)"]
    UPSERT["Upserter\n(Qdrant)"]
  end

  %% User to UI to API
  USER(("End User")) -->|HTTP(S)| UI
  UI -->|/v1/* via proxy| API

  %% API internals
  API --> AUTH
  API --> RATELIMIT
  API --> RAG
  RAG --> RETRIEVER
  RETRIEVER -->|vector search| QDRANT
  RETRIEVER -->|optional rerank| RAG
  RAG -->|LLM calls| OPENAI
  RAG -.->|optional| OLLAMA

  %% Ingestion path
  CRAWL --> PARSE --> CHUNK --> EMBED --> UPSERT --> QDRANT

  %% Config and Env
  subgraph CFG[Configuration]
    ENV[".env / pydantic-settings"]
  end
  ENV -.-> API
  ENV -.-> ING
  ENV -.-> QDRANT

  %% Networks & Containers
  subgraph DC[Docker Compose Network]
    API
    QDRANT
  end

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

# AI-CDSS — Codebase & Workflow Notes

A complete walkthrough of how the AI Clinical Decision Support System is put together, how a request flows through it, and where each responsibility lives.

---

## 1. What the system is

A Retrieval-Augmented Generation (RAG) assistant for clinicians:

1. A **knowledge base** of medical content (MedQuAD Q&A, guideline PDFs, crawled NCBI/CDC pages) is chunked, embedded and stored in **Qdrant**.
2. A clinician asks a question (optionally after uploading a **patient report** — PDF or image).
3. The backend rewrites the question, classifies it, retrieves + reranks evidence, and prompts an LLM (OpenAI or Ollama) to write a grounded, sectioned answer with citations.
4. The **React UI** renders the answer, the evidence sources, follow-up suggestions and the extracted patient context.

```
┌──────────────┐   /v1/chat, /patient/*    ┌────────────────────────┐   search   ┌──────────┐
│  React UI    │ ────────────────────────▶ │ FastAPI  (ai/app/api)  │ ─────────▶ │  Qdrant  │
│  (ui/, Vite) │ ◀──────────────────────── │  RAGPipeline           │ ◀───────── │ (HNSW)   │
└──────────────┘   answer + sources        │  ClinicalParser / OCR  │            └──────────┘
                                            │  SessionManager (RAM)  │ ──▶ OpenAI / Ollama LLM
                                            └────────────────────────┘ ──▶ Embeddings (OpenAI / MiniLM)
                                                       ▲
                     offline ingestion scripts ────────┘  (crawl → parse → chunk → embed → upsert)
```

---

## 2. Repository layout

| Path | What lives there |
|---|---|
| `ui/` | React 18 + Vite 6 + Tailwind v4 SPA (the clinician interface) |
| `ai/app/api/` | FastAPI app (`main.py`), routers: `routes_chat.py`, `routes_patient.py`, `routes_admin.py`, singletons in `deps.py` |
| `ai/app/core/` | `config.py` (env settings), `schemas.py` (Pydantic I/O), `prompts.py` (RAG prompt), `memory.py` (patient sessions), `security.py`, `logging.py` (PII masking), `constants.py`, `utils.py` |
| `ai/app/generation/` | `pipeline.py` (RAG orchestration), `llm.py` (OpenAI/Ollama providers), `query_rewriter.py`, `response_sizer.py` (query classifier → response policy) |
| `ai/app/vector/` | `embeddings.py`, `qdrant_client.py`, `retriever.py`, `reranker.py` (cross-encoder), `optimized_reranker.py` (parallel batches) |
| `ai/app/ingestion/` | `crawler.py`, `sitemap.py`, `parse_html.py`, `parse_pdf.py`, `cleaners.py`, `chunker.py`, `storage.py`, `models.py`, `clinical_parser.py` (patient-report extraction) |
| `ai/app/scripts/` | CLI jobs: `ingest_parquet.py`, `ingest_medquad.py`, `ingest_medical.py`, `ingest_web.py`, `rebuild_index.py`, `export_snapshot.py`, `eval_suite.py` |
| `ai/app/tests/` | pytest suites for chunker, embed/upsert, RAG pipeline |
| `docker-compose.yml` | `qdrant` (v1.7.0, ports 6333/6334) + `api` (uvicorn on 8000) |
| `docs/` | architecture diagram, ingestion guide, KB scripts, these notes |
| `paper_*.md`, `Literature survey/` | Research paper drafts and references (not part of runtime) |

---

## 3. Configuration (`ai/app/core/config.py`)

Loaded from `ai/.env` via `pydantic-settings`.

| Setting | Default | Meaning |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai` or `ollama` (`vllm` is declared but not implemented) |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | Chat model |
| `EMBEDDINGS_PROVIDER` | `openai` | `openai` (`text-embedding-3-small`, 1536-d) or `local` (`all-MiniLM-L6-v2`, 384-d). Falls back to local if no OpenAI key |
| `OLLAMA_MODEL` / `OLLAMA_HOST` | `llama3` / `localhost:11434` | Local LLM |
| `QDRANT_URL` | `http://qdrant:6333` | Use `http://localhost:6333` when running the API outside Docker |
| `COLLECTION_NAME` | `clinical_knowledge_v1` | Qdrant collection |
| `SIMILARITY_CUTOFF` | `0.22` | Minimum cosine score kept |
| `TOP_K` / `TOP_N` | `40` / `3` | Candidates retrieved / chunks kept after rerank (TOP_N is overridden by the response policy) |
| `API_KEY` | `dev-secret` | Required as `X-API-Key` on `/admin/*` |

> ⚠️ The embedding provider used at **query time must match** the one used at **ingestion time** (vector size must equal the collection's size).

---

## 4. Backend API surface (`ai/app/api`)

| Method & path | Router | Body | Returns |
|---|---|---|---|
| `GET /health` | main | – | `{status, version}` |
| `POST /v1/chat` | chat | `{query, history?, context?, filters?}` | `{answer_text, sources[], confidence, query_embedding_similarity[], follow_up_questions[]}` |
| `POST /patient/upload` | patient | multipart `file` (PDF / image) | `{session_id, structured_data, filename}` |
| `POST /patient/analyze` | patient | `{query, session_id}` | `{answer, sources[], confidence, follow_up_questions[]}` |
| `GET /admin/stats` | admin | header `X-API-Key` | collection stats |
| `POST /admin/reindex`, `/admin/ingest` | admin | header `X-API-Key` | stubs ("job queued") |
| `POST /admin/ingest_parquet` | admin | header `X-API-Key` | runs `ingest_parquet.main()` synchronously |

Startup (`deps.py`) instantiates **one** `RAGPipeline` and one Qdrant client at import time, so the embedding model, LLM client and cross-encoder are loaded once.

Note the two answer shapes: `/v1/chat` uses `answer_text`, `/patient/analyze` uses `answer`. The UI handles both.

---

## 5. Workflow A — General clinical question (`POST /v1/chat`)

`routes_chat.chat()` → `RAGPipeline.answer()` (`ai/app/generation/pipeline.py`):

| Step | Code | What happens |
|---|---|---|
| 0 | `query_rewriter.rewrite_query` | If there is history, the LLM rewrites the latest message into a standalone query (resolves "it", "that dose", …) using the last 4 turns |
| 1 | `response_sizer.classify_query` | Keyword-cue classifier picks one of 4 tiers → `ResponsePolicy(max_tokens, top_n, style_instruction)`:<br>• `clinical_scenario` (1500 tok, top 6) — "patient with…", "presents with…"<br>• `clinical_guidance` (1200 tok, top 5) — "manage", "treat", "diagnose"…<br>• `short_answer` (300 tok, top 3) — short/"what is"/"dose"<br>• `medium_explanation` (800 tok, top 4) — fallback |
| 2 | `embeddings.get_embedding` | Embed the rewritten query |
| 3 | `retriever.retrieve_with_cutoff` | Qdrant `query_points` (fallback `search`) for `top_k*2` candidates, then drop scores < 0.22, keep `top_k` |
| — | | **No chunks →** return `NO_KB_MSG` ("I don't have verifiable information…") with confidence `low` |
| 4 | `reranker` (+ `optimized_reranker`) | `cross-encoder/ms-marco-MiniLM-L-12-v2` scores (query, chunk) pairs in parallel batches of 8 / 3 threads; keeps `policy.top_n`. The rerank logit is passed through a sigmoid and replaces the cosine score; chunks below 0.05 relevance are dropped |
| 5 | pipeline | If history > 6 turns, the LLM produces a rolling summary (≤200 tokens) |
| 6 | `prompts.build_rag_prompt` | Builds a prompt with: patient context, KB chunks (JSONL: url/title/section/excerpt≤500 chars), history (last 10), summary, question, reasoning rules. For `medium`/`detailed` modes it forces 4 sections: **🧠 Clinical Interpretation / ⚠️ Risk Flags & Warnings / 📚 Evidence Basis / 📋 Actionable Next Steps** |
| 7 | `llm.generate` | temperature 0, `max_tokens = policy.max_tokens`, system prompt = "evidence-informed Clinical Decision Support Assistant" |
| 8 | pipeline | Strip any "Sources" section the model appended (UI shows sources separately) |
| 9 | pipeline | Build `sources[]` from chunks, dedupe by (url, char range) |
| 10 | pipeline | Confidence = mean score ≥0.8 high, ≥0.5 medium, else low |
| 11 | pipeline | Second small LLM call → 3–5 follow-up questions as a JSON array |

`routes_chat` clamps each source score into `[0, 1]` (rerank logits can be negative or >1) and returns `ChatResponse`.

---

## 6. Workflow B — Patient report upload & analysis

### B1. Upload (`POST /patient/upload`)
1. **Text extraction**
   - PDF → `parse_pdf.extract_pdf_text` (PyMuPDF)
   - Image → `pytesseract.image_to_string` (Tesseract must be installed)
   - Anything else → 400
2. **Structuring** → `ClinicalParser.parse_document` sends the first 4,000 chars to the LLM and asks for JSON:
   ```json
   { "demographics": {"age", "gender"}, "active_problems": [], "medications": [],
     "allergies": [], "labs": [{"test_name","value","unit"}], "unstructured_narrative": "" }
   ```
   If JSON parsing fails, everything is stuffed into `unstructured_narrative`.
3. **Abnormal-lab flagging** → `_detect_abnormal_labs` compares against hard-coded ranges (glucose, HbA1c, hemoglobin, WBC, platelets, Na, K, creatinine, BUN, troponin). Out-of-range → `High`/`Low`; troponin high → `Critical`; adds `reference_range`.
4. **Session** → `SessionManager.create_session` stores `{structured_data, history}` **in process memory** keyed by a UUID → returned to the UI.

### B2. Analyze (`POST /patient/analyze`)
1. Look up the session (404 if the server restarted — sessions are not persisted).
2. `PatientSession.format_context_for_prompt()` renders demographics, problems, narrative, meds, allergies, a highlighted `!!! ABNORMAL / CRITICAL LABS !!!` block, then normal labs.
3. `RAGPipeline.run()` executes the same Workflow A in a thread pool, with that text as `patient_context` and the session's history.
4. The Q/A pair is appended to session history (capped at last 10 messages).

---

## 7. Workflow C — Knowledge-base ingestion (offline)

All scripts run from `ai/` as `python -m app.scripts.<name>`.

| Script | Source | Notes |
|---|---|---|
| `ingest_parquet` | `ai/data.parquet` (MedQuAD) | First 11,000 rows, question+answer → one point each, UUID ids |
| `ingest_medquad` | MedQuAD via HF datasets | `--limit`, `--batch-size` |
| `ingest_medical` | local folder of PDFs/txt | `--directory`, `--pattern`; uses `chunk_page` |
| `ingest_web` | crawl seed URL / URL file | `--seed`, `--max-pages`, `--allow-prefix`, `--block-prefix`, `--only-pdf`, `--ignore-robots` … |
| `rebuild_index` | – | Recreate collection (`--force`) |
| `export_snapshot` | – | Qdrant snapshot to `snapshots/` |
| `eval_suite` | built-in clinical queries | Writes `eval_results.json` |

Web pipeline: `RespectfulCrawler` (robots.txt, rate-limit `RATE_LIMIT_RPS`) → `parse_html` (title, breadcrumbs, headings, FAQ pairs, tables) / `parse_pdf` → `cleaners` → `chunker.chunk_page` (section-aware, 800–1600 chars, 25 % overlap, sliding-window fallback) → `StorageManager` (raw/clean/chunks on disk under `data/`) → embed → upsert (`ensure_collection` sets cosine distance, HNSW m=64, ef_construct=128).

Payload stored per point: `url, title, section_heading, text, char_start, char_end, content_type, crawl_ts, last_modified, embedding_model, hash …` — exactly what `retriever.retrieve` reads back.

---

## 8. Frontend (`ui/`)

### Stack
React 18, TypeScript, Vite 6, Tailwind v4 (`@tailwindcss/postcss`) + typography plugin, `react-markdown` + `remark-gfm`, `lucide-react` icons.

### Dev proxy (`vite.config.ts`)
`/v1`, `/patient`, `/admin`, `/health` → `http://localhost:8000`. The UI calls relative URLs (override with `VITE_API_URL`).

### UI structure (after the Glass-style redesign)

```
src/
  main.tsx               – mounts <App/> inside ErrorBoundary
  App.tsx                – state: encounters, active encounter, send/upload orchestration
  api.ts                 – fetch wrappers for /v1/chat, /patient/upload, /patient/analyze
  types.ts               – Message, Source, Encounter, PatientData …
  utils/encounters.ts     – localStorage persistence + helpers
  utils/citations.ts      – turns "[Ref 1]" / "[1]" into citation chips
  components/
    Sidebar.tsx          – collapsible rail: New, Upload report, Search, patient context, encounter history
    Home.tsx             – centered hero ("Clinical Intelligence to …"), composer, quick-action chips
    Composer.tsx         – auto-growing input card, upload button, send
    QuickActions.tsx     – chip rail (Draft DDx, Draft A&P, Interpret Labs…); clicking a chip opens a list of
                           verified example prompts (Glass-style: inline on Home, popover in a conversation)
    ChatColumn.tsx       – left column: user bubbles, "Response generated" reasoning steps, answer cards, follow-ups
    DocumentPanel.tsx    – right panel: tabbed answers / patient overview, sources, copy/print
    PatientOverview.tsx  – demographics, problems, meds, allergies, labs table with flags
    Markdown.tsx         – markdown renderer with citation superscripts
```

### Front-end request flow
1. **Upload** → `POST /patient/upload` → store `session_id` + `structured_data` on the current encounter → "Patient Overview" tab appears.
2. **Send**:
   - encounter has `session_id` → `POST /patient/analyze {query, session_id}`
   - otherwise → `POST /v1/chat {query, history}`
3. While waiting, the reasoning steps animate (context → analyze → retrieve → generate). They are client-side timers — the backend is not streaming.
4. The answer is added to the chat column as a card and opened in the right document panel; `follow_up_questions` become clickable chips.
5. Encounters (messages, patient data, session id) persist in `localStorage`. If the API restarted, `/patient/analyze` returns 404 and the UI asks to re-upload.

---

## 9. Running locally

For the local Ollama demo setup see [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md).

```bash
docker run -p 6333:6333 qdrant/qdrant                   # 1. vector DB
cd ai && cp .env.example .env                            # 2. set OPENAI_API_KEY, QDRANT_URL=http://localhost:6333
python3 -m venv venv && source venv/bin/activate && pip install -e .
python -m app.scripts.ingest_parquet                     # 3. seed knowledge base (once)
uvicorn app.api.main:app --port 8000 --reload            # 4. API → http://localhost:8000/docs
cd ../ui && npm install && npm run dev                   # 5. UI  → http://localhost:5173
```

Or `docker-compose up -d --build` for Qdrant + API (the UI still runs with `npm run dev`).

---

## 10. Known gaps / things to watch

- **Sessions are in-memory** (`core/memory.py`) — lost on restart, not shared across workers. Redis/DB needed for production.
- **`/admin/reindex` and `/admin/ingest` are stubs**; `/admin/ingest_parquet` blocks the request thread.
- **Response shape mismatch** between `/v1/chat` (`answer_text`) and `/patient/analyze` (`answer`).
- Confidence thresholds (0.8/0.5) are applied to sigmoid rerank relevance — reasonable but not clinically calibrated.
- **No streaming** — the reasoning steps in the UI are simulated.
- `constants.ADVICE_KEYWORDS`, `cleaners.preserve_irs_form_numbers`, the Makefile `ingest` target and `docs/architecture.md` title are leftovers from an earlier IRS-RAG project.
- `pyproject` scripts reference `app.scripts.ingest:main`, which doesn't exist (use `ingest_web`).
- CORS is `*`; lock down for production.
- Lab reference ranges are hard-coded and adult/unit-agnostic.

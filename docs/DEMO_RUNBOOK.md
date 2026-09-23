# Demo Runbook (local, fully offline-capable)

Stack: **Qdrant** (Docker) · **FastAPI API** (Docker) · **Ollama llama3.2 3B** (native macOS, Metal GPU) · **React UI** (Vite dev server).
Knowledge base: 11,000 MedQuAD (NIH) Q&A points, embedded with `all-MiniLM-L6-v2` (384-d), reranked with `ms-marco-MiniLM-L-12-v2`.

## Start (≈1 minute)

1. Open **Docker Desktop** and the **Ollama** app (menu-bar llama icon).
2. From the repo root:
   ```bash
   docker compose -f docker-compose.demo.yml up -d
   ```
3. Warm the model so the first answer isn't slow:
   ```bash
   curl -s localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"hi","stream":false}' > /dev/null
   ```
4. Start the UI:
   ```bash
   npm --prefix ui run dev
   ```
5. Open http://localhost:5173

### Health checks
```bash
curl localhost:8000/health                                   # {"status":"healthy"...}
curl -s localhost:6333/collections/clinical_knowledge_v1 | grep -o '"points_count":[0-9]*'   # 11000
```
API docs (nice to show): http://localhost:8000/docs · Qdrant dashboard: http://localhost:6333/dashboard

## Stop
```bash
docker compose -f docker-compose.demo.yml stop
```
(`down` is fine too — the vectors live in the `qdrant_storage` volume. Only `down -v` deletes them.)

## Re-ingest the knowledge base (only if the collection is missing, ~7 min)
```bash
docker exec -d -w /app ai-cdss-api sh -c 'python -m app.scripts.ingest_parquet > /app/data/ingest.log 2>&1'
```
Run it **once** — the script uses random ids, so parallel/duplicate runs create duplicate points.

## Demo materials

Everything for the demo is in [`demo/`](../demo): the synthetic patient report (PDF + scanned PNG) and
**[`demo/DEMO_QUERIES.md`](../demo/DEMO_QUERIES.md)**, the verified query script with expected results.

## Suggested demo flow (~5 min)

1. **General question, grounded in the KB** — *"What causes glaucoma and how is it diagnosed?"*
   → high confidence, 5 sources, click a `[1]` citation to jump to its reference.
   Other good ones: *"How is Parkinson's disease treated?"*
2. **Upload a patient report** — `demo/patient_report_maria_alvarez.pdf` (64F, CKD stage 4, T2DM, anemia, on metformin + lisinopril + ibuprofen).
   → Patient Overview tab: 6 problems, 6 meds, 2 allergies, 13 labs with 11 flagged (troponin Critical).
3. **Patient-grounded questions** — the **Drug Interactions** / **Interpret Labs** chips (click a chip → pick an example).
4. **Follow-up chip** — shows conversational memory (query rewriting).
5. Talking points: RAG pipeline (retrieve → rerank → relevance threshold → grounded prompt), confidence derived from evidence relevance,
   answers say *"based on general clinical knowledge"* when the KB has no matching evidence instead of inventing citations.

## Expectations / limitations to mention
- Answers take **~20–60 s** (3B model on a laptop; complex case questions are allowed up to 1,500 tokens).
- The 3B model can make clinical reasoning errors — it is decision *support*, and a larger model (e.g. `llama3.1:8b`,
  needs ~5 GB free disk) or GPT-4o-mini (`LLM_PROVIDER=openai`) would give noticeably better answers with no code change.
- The KB is consumer-level NIH Q&A, so specialist questions (drug interactions, cardiology management) often get *low confidence*.
- Patient sessions are in memory — if the API container restarts, re-upload the report.

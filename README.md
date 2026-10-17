# Clinical Decision Support System (AI-CDSS)

A research prototype: a Retrieval-Augmented Generation (RAG) service and React dashboard for clinical decision support. Answers carry citations to the retrieved passages that produced them, and patient documents (PDF or image) can be uploaded for context.

> **Status: research prototype. Not evaluated, not validated, not for clinical use.**
> No retrieval-quality, answer-correctness or hallucination evaluation has been performed.
> The paper drafts in this repository previously reported such results; those results were never measured and have been withdrawn.
> For work on this system that *is* measured, see the fault-injection study described below.

## 🏗 Architecture

The platform consists of three main components:

- **Frontend (UI)**: React / Vite SPA providing the clinical interface, patient context sidebar, and citation-supported chat. Located in `ui/`.
- **Backend (API)**: Python / FastAPI service handling RAG pipelines, OCR text extraction, and LLM orchestration. Located in `ai/`.
- **Vector Database**: Qdrant, used for storing medical document embeddings and fast vector search.

### Tech Stack Details:
- **Language**: Python 3.11+ (Backend), TypeScript/JavaScript (Frontend)
- **Vector DB**: Qdrant
- **OCR**: Tesseract + Pillow for medical images
- **Embeddings**: OpenAI or Local (`all-MiniLM-L6-v2`)
- **LLM**: GPT-4o or Ollama (`llama3`, `meditron`)
- **PDF Parsing**: PyMuPDF

## ✨ Features

- **Clinical Knowledge Base**: Ingests medical guidelines and journals (HTML and PDFs).
- **Patient Context Aware**: Upload patient reports (PDF) and images to ground AI analysis.
- **Citation system**: answers cite the retrieved passages by reference number, and markers that do not resolve to a retrieved passage are stripped before display. A resolvable citation means the reference points at a retrieved chunk — **not** that the chunk supports the sentence citing it.
- **Clinical Chat UI**: Markdown-rendered chat with reference viewers.
- **Fallbacks**: an explicit "no verifiable information" path when nothing clears the retrieval similarity cutoff. *(Note: the legal-disclaimer injection in `pipeline.py` is currently commented out.)*
- **Multi-format Support**: Handles HTML, PDFs, and Medical Images (OCR).

## 🛠 Prerequisites

- **Docker** and **Docker Compose**
- **Node.js** (for running frontend locally)
- **Python 3.11+** (for running backend locally)
- **Tesseract OCR**: Required for image analysis.
  - Mac: `brew install tesseract`
  - Linux: `apt-get install tesseract-ocr`

## 🚀 Running the Application

### Option 1: Using Docker Compose (Recommended)

Start the entire stack (Backend API + Vector DB + Frontend) using Docker Compose:

```bash
docker-compose up -d --build
```

### Option 2: Running Locally for Development

To run the frontend and backend services separately on your host machine:

#### 1. Start Vector DB (Qdrant)
Ensure Qdrant is running, e.g., via Docker:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

#### 2. Start Backend (API)
```bash
cd ai
cp .env.example .env
# Edit .env with your specific API keys, QDRANT_URL, etc., if needed.

# 1. Create a virtual environment
python3 -m venv venv

# 2. Activate the virtual environment
# On macOS and Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# 3. Install the required dependencies
pip install -e .

# 4. Start FastAPI server
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```
The API will be available at `http://localhost:8000`. API Documentation (Swagger) is at `http://localhost:8000/docs`.

#### 3. Start Frontend (UI)
```bash
cd ui
npm install
npm run dev
```
Access the UI at `http://localhost:5173`. Ensure the backend is running on port 8000.

## 📚 Data Ingestion Commands

To populate the Knowledge Base, you can ingest local medical documents or crawl web sources. Run these commands from the `ai/` directory:

### Ingest Local Medical PDFs
Place your medical PDFs in a directory (e.g., `ai/data/medical_docs`) and run:
```bash
python -m app.scripts.ingest_medical --directory ./data/medical_docs
```

### Ingest Web Content (e.g., CDC/NCBI)
```bash
python -m app.scripts.ingest_web --seed "https://www.cdc.gov/flu/" --max-pages 500
```

## 🧪 Testing & Evaluation

**Unit tests** (from `ai/`):
```bash
PYTHONPATH=. python -m pytest app/tests/ -q
```

**Smoke / instrumentation suite** over 20 clinical information queries:
```bash
python -m app.scripts.eval_suite --output-file eval_results.json
```
This reports retrieval hit rate, abstention rate, citation presence, citation
*resolvability* and latency. It does **not** measure retrieval precision,
answer correctness, citation support or hallucination rate, and its output must
not be described as if it did. See the module docstring.

Note the CI workflow lives at `ai/infra/github-actions/ci.yml` and is **not** in
`.github/workflows/`, so GitHub does not currently run it.

### Fault-injection study (measured)

A controlled study of the document-image path — OCR → extraction →
abnormal-value flagging — using a synthetic report with machine-readable
ground truth for 13 analytes: 832 analyte observations across 32 image
degradation conditions, behind a calibration gate that refuses to report any
degradation figure unless the undegraded render extracts perfectly.

Headline results: at 150 dpi, 98.3% of characters are read correctly while 15%
of laboratory values are wrong; 65% of corrupted values kept the same
abnormal-value flag as the true value. The plausibility check now in
`clinical_parser.py` converts 9 of those 28 silent corruptions into visible
ones — the other 19 remain invisible.

## 🔒 Security & Compliance

- **TLS/HTTPS**: Required in production (TLS termination at load balancer).
- **API Key Auth**: Required for admin endpoints.
- **Rate Limiting**: Per-IP rate limits via `slowapi`.
- **PII Masking**: Logs mask sensitive identifiers.
- **Encryption**: Qdrant at-rest encryption (if managed).

## ⚠️ Limitations

- **Scope**: Medical guidelines only.
- **No live web**: Answers are based on indexed content.
- **No medical advice**: System provides information, not diagnosis. Always consult a qualified physician.

## License
MIT

---

## Ownership and licence

Copyright (c) 2025-2026 **Mohammed Jabir Hussain Shaik** ([@thejabirhussain](https://github.com/thejabirhussain)). **All rights reserved.**

This is proprietary work, published for viewing and evaluation only. Copying, reusing, modifying, redistributing, using it to train AI models, or presenting any part of it as your own is **not permitted** without written permission. See [LICENSE](LICENSE). Permission requests: thejabirhussain@gmail.com

# Clinical Decision Support System (AI-CDSS)

A production-ready Retrieval-Augmented Generation (RAG) service and React-based dashboard for Clinical Decision Support. The system provides verifiable citations for every answer from trusted medical guidelines and supports patient data analysis.

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
- **Evidence-Based & Citation System**: Answers queries using retrieved medical sources with specific section/page citations.
- **Clinical Chat UI**: Markdown-rendered chat with reference viewers.
- **Guardrails**: Clinical disclaimers and "unknown" fallbacks for safety.
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

# Start FastAPI server
# Note: Ensure your virtual environment is activated and dependencies are installed.
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

Run the backend evaluation suite with clinical queries from the `ai/` directory:
```bash
python -m app.scripts.eval_suite --output-file eval_results.json
```

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

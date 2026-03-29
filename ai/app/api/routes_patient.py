from typing import Optional
import io
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from PIL import Image
import pytesseract

from app.ingestion.parse_pdf import extract_pdf_text
from app.api.deps import get_rag_pipeline
from app.generation.pipeline import RAGPipeline

from app.ingestion.clinical_parser import get_clinical_parser
from app.core.memory import get_session_manager

router = APIRouter()

class PatientAnalysisRequest(BaseModel):
    query: str
    session_id: str  # Use session ID instead of raw context string

class PatientUploadResponse(BaseModel):
    session_id: str
    structured_data: dict
    filename: str

@router.post("/upload", response_model=PatientUploadResponse)
async def upload_patient_file(file: UploadFile = File(...)):
    """
    Upload a patient file (PDF or Image), extract raw text, and parse into a structured clinical schema.
    Returns the structured JSON and a Session ID to maintain context for analysis.
    """
    content = await file.read()
    raw_text = ""
    metadata = {}

    # 1. OCR or PDF Extraction
    if file.content_type == "application/pdf":
        raw_text, metadata = extract_pdf_text(content)
    elif file.content_type.startswith("image/"):
        try:
            image = Image.open(io.BytesIO(content))
            raw_text = pytesseract.image_to_string(image)
            metadata = {"source": "ocr", "format": file.content_type}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Only PDF and Image files are supported.")
    
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract any text from the document.")

    # 2. Structured Parsing & Abnormal Detection
    parser = get_clinical_parser()
    structured_data = parser.parse_document(raw_text)

    # 3. Create Session
    session_manager = get_session_manager()
    session_id = session_manager.create_session(structured_data)
    
    return {
        "session_id": session_id,
        "structured_data": structured_data,
        "filename": file.filename
    }

@router.post("/analyze")
async def analyze_patient_case(
    request: PatientAnalysisRequest,
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
):
    """
    Analyze a patient case using persistent Clinical Memory and RAG.
    Maintains history context through the SessionManager.
    """
    session_manager = get_session_manager()
    session = session_manager.get_session(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Patient session not found or expired. Please upload the document again.")
    
    # Generate the highly structured patient context for the LLM
    context_str = session.format_context_for_prompt()
    
    # Run the pipeline with the specific patient context and historical memory
    result = await pipeline.run(
        user_query=request.query,
        history=session.history,
        patient_context=context_str
    )
    
    # Append to memory
    session.add_interaction(request.query, result["answer"])
    
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "confidence": result.get("confidence", "high"),
        "follow_up_questions": result.get("follow_up_questions", [])
    }


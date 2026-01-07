from typing import Optional
import io
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from PIL import Image
import pytesseract

from app.ingestion.parse_pdf import extract_pdf_text
from app.api.deps import get_rag_pipeline
from app.generation.pipeline import RAGPipeline

router = APIRouter()

class PatientAnalysisRequest(BaseModel):
    query: str
    patient_context: str  # Extracted text from uploaded files
    history: Optional[list[dict]] = None

class PatientAnalysisResponse(BaseModel):
    answer: str
    sources: list[dict]

@router.post("/upload")
async def upload_patient_file(file: UploadFile = File(...)):
    """
    Upload a patient file (PDF or Image) and extract text.
    For MVP, we return the text to the client to send back in analysis requests.
    """
    content = await file.read()
    text = ""
    metadata = {}

    if file.content_type == "application/pdf":
        text, metadata = extract_pdf_text(content)
    elif file.content_type.startswith("image/"):
        try:
            image = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(image)
            metadata = {"source": "ocr", "format": file.content_type}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")
    else:
        raise HTTPException(status_code=400, detail="Only PDF and Image files are supported.")
    
    return {"filename": file.filename, "extracted_text": text, "metadata": metadata}

@router.post("/analyze")
async def analyze_patient_case(
    request: PatientAnalysisRequest,
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
):
    """
    Analyze a patient case using RAG + Patient Context.
    """
    # Construct a query that includes the patient context implicitly or explicitly
    # We'll use the pipeline's run method but might need to inject the context into the prompt
    # The existing pipeline might accept 'summary' or we can prepend to query.
    
    # Strategy: Prepend patient context to the user query effectively acting as "Here is the case, answer this question"
    # Or better, we can treat patient_context as a "system" injection or "conversation summary".
    
    combined_query = f"""
    [PATIENT DATA START]
    {request.patient_context}
    [PATIENT DATA END]
    
    USER QUESTION: {request.query}
    """
    
    # We use the pipeline to generate response
    # The pipeline will search knowledge base for MEDICAL GUIDELINES relevant to the query + patient data keys
    result = await pipeline.run(
        user_query=combined_query,
        history=request.history or []
    )
    
    return {
        "answer": result["answer"],
        "sources": result["sources"]
    }

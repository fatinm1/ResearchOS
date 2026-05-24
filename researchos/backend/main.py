import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.models import HealthResponse
from backend.pipeline.classifier import classify_amendment
from backend.pipeline.docgen import generate_word_doc
from backend.pipeline.drafter import draft_amendment
from backend.pipeline.extractor import extract_pdf_text
from backend.pipeline.verifier import verify_consistency

load_dotenv()

BASE_DIR = Path(__file__).parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ResearchOS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend" / "static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_landing():
    """Serve the ResearchOS marketing landing page."""
    landing_page = BASE_DIR / "frontend" / "index.html"
    return HTMLResponse(content=landing_page.read_text())


@app.get("/app", response_class=HTMLResponse)
async def serve_app():
    """Serve the ResearchOS amendment drafting product app."""
    app_page = BASE_DIR / "frontend" / "app.html"
    return HTMLResponse(content=app_page.read_text())


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for CI and uptime monitoring."""
    return HealthResponse(status="ok", version="0.1.0", product="ResearchOS MVP")


@app.post("/api/generate-amendment")
async def generate_amendment(
    protocol_pdf: UploadFile = File(...),
    change_description: str = Form(...),
    pi_name: str = Form(""),
    study_title: str = Form(""),
    protocol_number: str = Form(""),
):
    """
    Main pipeline endpoint: extract PDF, classify, draft, verify, and generate Word document.

    Accepts a multipart form with the researcher's IRB protocol PDF and change description.
    Runs the three-stage Claude pipeline (classify → draft → verify) and generates a
    formatted Word document. Returns the .docx as a file download with pipeline metadata
    in response headers (X-Review-Type, X-Consistency-Score, X-Ready-To-Submit).
    """
    # Validate file type
    if not protocol_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF.")

    # Validate change description
    if not change_description or len(change_description.strip()) <= 20:
        raise HTTPException(
            status_code=400,
            detail="Change description must be more than 20 characters.",
        )

    # Read and validate file size
    pdf_bytes = await protocol_pdf.read()
    if len(pdf_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 20MB.")
    if len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY is not configured. Contact the administrator.",
        )

    try:
        # Stage 0: Extract PDF text
        protocol_text = extract_pdf_text(pdf_bytes)

        # Stage 1: Classify review type
        classification = classify_amendment(change_description, protocol_text)

        # Stage 2: Draft amendment sections
        draft = draft_amendment(change_description, protocol_text, classification)

        # Stage 3: Verify consistency
        verification = verify_consistency(draft, protocol_text, change_description)

        # Generate Word document
        doc_path = generate_word_doc(
            change_description=change_description,
            classification=classification,
            draft=draft,
            verification=verification,
            pi_name=pi_name,
            study_title=study_title,
            protocol_number=protocol_number,
            outputs_dir=OUTPUTS_DIR,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(exc)}") from exc

    headers = {
        "X-Review-Type": classification.get("review_type", "EXPEDITED"),
        "X-Consistency-Score": str(verification.get("consistency_score", 5)),
        "X-Ready-To-Submit": str(verification.get("ready_to_submit", False)),
        "Access-Control-Expose-Headers": "X-Review-Type, X-Consistency-Score, X-Ready-To-Submit",
    }

    return FileResponse(
        path=str(doc_path),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=doc_path.name,
        headers=headers,
    )


if not os.environ.get("ANTHROPIC_API_KEY"):
    import warnings

    warnings.warn("ANTHROPIC_API_KEY not set. API calls will fail.", RuntimeWarning)

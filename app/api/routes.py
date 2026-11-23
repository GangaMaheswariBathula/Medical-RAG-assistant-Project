"""REST endpoints: /upload /ask /health /sources /stats"""
import asyncio
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.chains.rag_chain import RAGChain
from app.config import get_settings
from app.dependencies import get_rag_chain
from app.exceptions import FileTooLargeError, UnsupportedFileError
from app.loaders.document_loader import load_document, split_documents
from app.logger import get_logger
from app.utils.validators import safe_filename, sanitize_question

logger = get_logger(__name__)
router = APIRouter()


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    top_k: int | None = Field(None, ge=1, le=10)
    filename: str | None = None


class Source(BaseModel):
    filename: str
    page: int
    score: float
    text: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    latency_ms: float


def _clean_question(raw: str) -> str:
    question = sanitize_question(raw)
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")
    if len(question) > get_settings().max_question_chars:
        raise HTTPException(status_code=400, detail="Question is too long.")
    return question


@router.get("/health")
async def health():
    s = get_settings()
    return {
        "status": "ok",
        "groq_key_set": bool(s.groq_api_key),
        "pinecone_key_set": bool(s.pinecone_api_key),
    }


@router.post("/upload")
async def upload(file: UploadFile = File(...), chain: RAGChain = Depends(get_rag_chain)):
    s = get_settings()
    filename = safe_filename(file.filename)
    ext = Path(filename).suffix.lower()
    if ext not in s.allowed_extensions:
        raise UnsupportedFileError(f"Unsupported file type '{ext}'. Allowed: {s.allowed_extensions}")

    content = await file.read(s.max_upload_bytes + 1)  # read one extra byte to detect oversize
    if len(content) > s.max_upload_bytes:
        raise FileTooLargeError(f"File exceeds {s.max_upload_mb} MB limit.")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        def _process():
            docs = load_document(tmp_path, filename)
            chunks = split_documents(docs)
            return {"filename": filename, "pages": len(docs), "chunks": chain.ingest(chunks)}

        result = await asyncio.to_thread(_process)  # keep the event loop free
    finally:
        os.unlink(tmp_path)
    logger.info("Upload complete: %s", result)
    return result


@router.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest, chain: RAGChain = Depends(get_rag_chain)):
    question = _clean_question(body.question)
    logger.info("Question received (%d chars)", len(question))
    return await asyncio.to_thread(chain.ask, question, body.top_k, body.filename)


@router.get("/sources")
async def sources(
    question: str = Query(..., min_length=1, max_length=1000),
    top_k: int | None = Query(None, ge=1, le=10),
    filename: str | None = None,
    chain: RAGChain = Depends(get_rag_chain),
):
    """Return the supporting chunks for a question, without calling the LLM."""
    question = _clean_question(question)
    chunks = await asyncio.to_thread(chain.retrieve, question, top_k, filename)
    return {"question": question, "sources": chunks}


@router.get("/stats")
async def stats(chain: RAGChain = Depends(get_rag_chain)):
    return await asyncio.to_thread(chain.stats)

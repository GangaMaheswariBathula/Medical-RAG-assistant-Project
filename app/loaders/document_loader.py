"""Load PDF / TXT / DOCX files, clean them, and split into chunks."""
from pathlib import Path

from app.config import get_settings
from app.exceptions import EmptyDocumentError, UnsupportedFileError
from app.logger import get_logger
from app.utils.text_cleaner import strip_headers_footers

logger = get_logger(__name__)


def load_document(path: str, filename: str):
    """Return a list of cleaned LangChain Documents (one per non-blank page)."""
    from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
    from langchain_core.documents import Document

    ext = Path(filename).suffix.lower()
    loaders = {
        ".pdf": lambda: PyPDFLoader(path),
        ".txt": lambda: TextLoader(path, encoding="utf-8"),
        ".docx": lambda: Docx2txtLoader(path),
    }
    if ext not in loaders:
        raise UnsupportedFileError(f"Unsupported file type '{ext}'. Allowed: {sorted(loaders)}")

    raw_docs = loaders[ext]().load()
    cleaned = strip_headers_footers([d.page_content for d in raw_docs])

    docs = []
    for i, (raw, text) in enumerate(zip(raw_docs, cleaned)):
        if not text:  # blank page
            continue
        page = int(raw.metadata.get("page", i)) + 1  # PyPDF pages are 0-based
        docs.append(Document(page_content=text, metadata={"filename": filename, "page": page}))

    if not docs:
        raise EmptyDocumentError("No readable text found. Scanned PDFs need OCR first.")
    logger.info("Loaded %s: %d non-blank pages", filename, len(docs))
    return docs


def split_documents(docs):
    """Split documents into overlapping chunks using the settings in config.py."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    s = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=s.chunk_size, chunk_overlap=s.chunk_overlap
    )
    chunks = splitter.split_documents(docs)
    logger.info("Split into %d chunks (size=%d, overlap=%d)", len(chunks), s.chunk_size, s.chunk_overlap)
    return chunks

"""Custom exceptions. main.py maps each one to an HTTP status code."""


class RAGError(Exception):
    """Base class for all application errors."""


class ConfigError(RAGError):
    """Missing or invalid configuration (e.g. API key not set)."""


class UnsupportedFileError(RAGError):
    """Uploaded file type is not allowed."""


class FileTooLargeError(RAGError):
    """Uploaded file exceeds the size limit."""


class EmptyDocumentError(RAGError):
    """No readable text found in the document."""


class ExternalServiceError(RAGError):
    """Pinecone, Groq or the embedding model failed."""

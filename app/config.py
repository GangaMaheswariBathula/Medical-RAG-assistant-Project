"""Central configuration. Values come from environment variables / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API keys (never hardcode; set in .env or Render dashboard)
    groq_api_key: str = ""
    pinecone_api_key: str = ""

    # Pinecone
    pinecone_index_name: str = "medical-rag"
    pinecone_cloud: str = "aws"
    pinecone_region: str = "us-east-1"

    # Embeddings (bge-small-en-v1.5 and all-MiniLM-L6-v2 are both 384-dim)
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384

    # LLM
    # Groq retired llama-3.3-70b-versatile for developer-tier accounts.
    llm_model: str = "openai/gpt-oss-120b"
    temperature: float = 0.1
    max_tokens: int = 800

    # Chunking and retrieval
    chunk_size: int = 800
    chunk_overlap: int = 150
    top_k: int = 4
    min_score: float = 0.35  # chunks below this cosine score are ignored; tune it

    # Validation limits
    max_upload_mb: int = 10
    max_question_chars: int = 1000
    allowed_extensions: list[str] = [".pdf", ".txt", ".docx"]

    log_level: str = "INFO"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()

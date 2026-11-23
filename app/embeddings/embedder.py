"""Reusable embedding class with a small in-memory cache for queries."""
from functools import lru_cache

from app.config import get_settings
from app.logger import get_logger

logger = get_logger(__name__)


class Embedder:
    def __init__(self, model_name: str | None = None):
        from langchain_huggingface import HuggingFaceEmbeddings

        name = model_name or get_settings().embedding_model
        logger.info("Loading embedding model %s", name)
        self._model = HuggingFaceEmbeddings(
            model_name=name, encode_kwargs={"normalize_embeddings": True}
        )
        self._cache: dict[str, list[float]] = {}

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        if text not in self._cache:
            if len(self._cache) > 1000:
                self._cache.clear()
            self._cache[text] = self._model.embed_query(text)
        return self._cache[text]


@lru_cache
def get_embedder() -> Embedder:
    """One shared instance, so the model loads only once."""
    return Embedder()

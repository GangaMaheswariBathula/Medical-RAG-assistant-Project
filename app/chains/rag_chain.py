"""Modular RAG pipeline: question -> embed -> retrieve -> prompt -> LLM -> answer."""
import time

from app.config import get_settings
from app.embeddings.embedder import get_embedder
from app.exceptions import ConfigError, ExternalServiceError
from app.logger import get_logger
from app.prompts.prompt_builder import NO_ANSWER, build_messages
from app.services.llm_service import LLMService
from app.vectorstore.pinecone_store import PineconeStore

logger = get_logger(__name__)


class RAGChain:
    """Components are created lazily, so the API starts even before keys are set."""

    def __init__(self, embedder=None, store=None, llm=None):
        self._embedder, self._store, self._llm = embedder, store, llm

    # ---- lazy components -------------------------------------------------
    @property
    def embedder(self):
        if self._embedder is None:
            try:
                self._embedder = get_embedder()
            except Exception as exc:
                logger.exception("Embedding model failed to load")
                raise ExternalServiceError("Embedding model unavailable") from exc
        return self._embedder

    @property
    def store(self):
        if self._store is None:
            try:
                self._store = PineconeStore()
            except ConfigError:
                raise
            except Exception as exc:
                logger.exception("Pinecone connection failed")
                raise ExternalServiceError("Pinecone is unavailable") from exc
        return self._store

    @property
    def llm(self):
        if self._llm is None:
            try:
                self._llm = LLMService()
            except ConfigError:
                raise
            except Exception as exc:
                logger.exception("Groq client failed")
                raise ExternalServiceError("Groq is unavailable") from exc
        return self._llm

    # ---- pipeline steps --------------------------------------------------
    def ingest(self, chunks, batch_size: int = 64) -> int:
        """Embed chunks and store them in Pinecone. Returns number stored."""
        try:
            texts = [c.page_content for c in chunks]
            embeddings: list[list[float]] = []
            for i in range(0, len(texts), batch_size):
                embeddings.extend(self.embedder.embed_documents(texts[i : i + batch_size]))
            return self.store.upsert_chunks(chunks, embeddings)
        except (ConfigError, ExternalServiceError):
            raise
        except Exception as exc:
            logger.exception("Ingestion failed")
            raise ExternalServiceError("Ingestion failed (Pinecone unavailable?)") from exc

    def retrieve(self, question: str, top_k: int | None = None, filename: str | None = None):
        s = get_settings()
        start = time.perf_counter()
        try:
            vector = self.embedder.embed_query(question)
            matches = self.store.query(vector, top_k or s.top_k, filename)
        except (ConfigError, ExternalServiceError):
            raise
        except Exception as exc:
            logger.exception("Retrieval failed")
            raise ExternalServiceError("Retrieval failed (Pinecone unavailable?)") from exc
        kept = [m for m in matches if m["score"] >= s.min_score]
        logger.info(
            "Retrieved %d/%d chunks above min_score in %.0f ms",
            len(kept), len(matches), (time.perf_counter() - start) * 1000,
        )
        return kept

    def ask(self, question: str, top_k: int | None = None, filename: str | None = None) -> dict:
        started = time.perf_counter()
        chunks = self.retrieve(question, top_k, filename)

        if not chunks:  # empty retrieval: don't even call the LLM
            logger.info("Empty retrieval; returning fallback answer")
            return {"answer": NO_ANSWER, "sources": [], "latency_ms": _ms(started)}

        try:
            answer = self.llm.generate(build_messages(question, chunks))
        except (ConfigError, ExternalServiceError):
            raise
        except Exception as exc:
            logger.exception("LLM call failed")
            raise ExternalServiceError("Groq is unavailable") from exc

        latency = _ms(started)
        logger.info("Answered in %.0f ms using %d chunks", latency, len(chunks))
        return {"answer": answer, "sources": chunks, "latency_ms": latency}

    def stats(self) -> dict:
        try:
            return self.store.stats()
        except (ConfigError, ExternalServiceError):
            raise
        except Exception as exc:
            raise ExternalServiceError("Pinecone is unavailable") from exc


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)

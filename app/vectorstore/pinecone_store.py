"""Pinecone wrapper: auto-create index, upsert chunks, query, stats."""
import hashlib
import time

from app.config import get_settings
from app.exceptions import ConfigError
from app.logger import get_logger

logger = get_logger(__name__)


class PineconeStore:
    def __init__(self):
        from pinecone import Pinecone, ServerlessSpec

        s = get_settings()
        if not s.pinecone_api_key:
            raise ConfigError("PINECONE_API_KEY is not set")
        self._s = s
        self._pc = Pinecone(api_key=s.pinecone_api_key)
        self._ensure_index(ServerlessSpec)
        self._index = self._pc.Index(s.pinecone_index_name)  # reused connection

    def _ensure_index(self, serverless_spec) -> None:
        name = self._s.pinecone_index_name
        if name in self._pc.list_indexes().names():
            return
        logger.info("Creating Pinecone index '%s'", name)
        self._pc.create_index(
            name=name,
            dimension=self._s.embedding_dimension,
            metric="cosine",
            spec=serverless_spec(cloud=self._s.pinecone_cloud, region=self._s.pinecone_region),
        )
        while not self._pc.describe_index(name).status["ready"]:
            time.sleep(1)

    def upsert_chunks(self, chunks, embeddings, batch_size: int = 100) -> int:
        vectors = []
        for chunk, vec in zip(chunks, embeddings):
            filename = chunk.metadata.get("filename", "unknown")
            page = chunk.metadata.get("page", 0)
            # deterministic id: re-uploading the same file overwrites, not duplicates
            vid = hashlib.sha1(f"{filename}|{page}|{chunk.page_content}".encode()).hexdigest()
            vectors.append(
                {
                    "id": vid,
                    "values": vec,
                    "metadata": {"text": chunk.page_content, "filename": filename, "page": page},
                }
            )
        for i in range(0, len(vectors), batch_size):
            self._index.upsert(vectors=vectors[i : i + batch_size])
        logger.info("Upserted %d vectors", len(vectors))
        return len(vectors)

    def query(self, vector: list[float], top_k: int, filename: str | None = None) -> list[dict]:
        kwargs = {"vector": vector, "top_k": top_k, "include_metadata": True}
        if filename:  # metadata filtering
            kwargs["filter"] = {"filename": {"$eq": filename}}
        result = self._index.query(**kwargs)
        return [
            {
                "text": m.metadata.get("text", ""),
                "filename": m.metadata.get("filename", "unknown"),
                "page": int(m.metadata.get("page", 0)),
                "score": float(m.score),
            }
            for m in result.matches
        ]

    def stats(self) -> dict:
        info = self._index.describe_index_stats()
        return {
            "index": self._s.pinecone_index_name,
            "total_vector_count": int(info.total_vector_count),
        }

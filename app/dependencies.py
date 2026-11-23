"""FastAPI dependencies. Tests override get_rag_chain with a fake."""
from functools import lru_cache

from app.chains.rag_chain import RAGChain


@lru_cache
def get_rag_chain() -> RAGChain:
    return RAGChain()

import pytest

from app.chains.rag_chain import RAGChain
from app.exceptions import ExternalServiceError
from app.prompts.prompt_builder import NO_ANSWER


class FakeEmbedder:
    def embed_query(self, text):
        return [0.1, 0.2]

    def embed_documents(self, texts):
        return [[0.1, 0.2] for _ in texts]


class FakeStore:
    def __init__(self, matches=None, fail=False):
        self.matches, self.fail = matches or [], fail

    def query(self, vector, top_k, filename=None):
        if self.fail:
            raise RuntimeError("pinecone down")
        return self.matches


class FakeLLM:
    def __init__(self, fail=False):
        self.calls, self.fail = 0, fail

    def generate(self, messages):
        self.calls += 1
        if self.fail:
            raise RuntimeError("groq down")
        return "Answer [doc.pdf, p.1]"


def chunk(score):
    return {"text": "t", "filename": "doc.pdf", "page": 1, "score": score}


def test_low_score_chunks_are_filtered_and_llm_skipped():
    llm = FakeLLM()
    chain = RAGChain(FakeEmbedder(), FakeStore([chunk(0.1)]), llm)
    result = chain.ask("anything")
    assert result["answer"] == NO_ANSWER
    assert result["sources"] == []
    assert llm.calls == 0


def test_good_retrieval_calls_llm_and_returns_sources():
    chain = RAGChain(FakeEmbedder(), FakeStore([chunk(0.9)]), FakeLLM())
    result = chain.ask("question")
    assert result["answer"].startswith("Answer")
    assert result["sources"][0]["filename"] == "doc.pdf"
    assert result["latency_ms"] >= 0


def test_pinecone_failure_becomes_external_service_error():
    chain = RAGChain(FakeEmbedder(), FakeStore(fail=True), FakeLLM())
    with pytest.raises(ExternalServiceError):
        chain.ask("question")


def test_groq_failure_becomes_external_service_error():
    chain = RAGChain(FakeEmbedder(), FakeStore([chunk(0.9)]), FakeLLM(fail=True))
    with pytest.raises(ExternalServiceError):
        chain.ask("question")

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_rag_chain
from app.exceptions import ExternalServiceError
from app.main import app

SOURCE = {"filename": "doc.pdf", "page": 1, "score": 0.9, "text": "chunk text"}


class FakeChain:
    def ask(self, question, top_k=None, filename=None):
        return {"answer": "Fake answer [doc.pdf, p.1]", "sources": [SOURCE], "latency_ms": 5.0}

    def retrieve(self, question, top_k=None, filename=None):
        return [SOURCE]

    def ingest(self, chunks):
        return len(chunks)

    def stats(self):
        return {"index": "test", "total_vector_count": 42}


class FailingChain(FakeChain):
    def ask(self, *args, **kwargs):
        raise ExternalServiceError("Groq is unavailable")


@pytest.fixture
def client():
    app.dependency_overrides[get_rag_chain] = lambda: FakeChain()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_ask_returns_answer_and_sources(client):
    r = client.post("/ask", json={"question": "What is diabetes?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"].startswith("Fake answer")
    assert body["sources"][0]["filename"] == "doc.pdf"


def test_ask_empty_question_rejected(client):
    assert client.post("/ask", json={"question": ""}).status_code == 422


def test_ask_whitespace_question_rejected(client):
    assert client.post("/ask", json={"question": "    "}).status_code == 400


def test_ask_external_failure_returns_503():
    app.dependency_overrides[get_rag_chain] = lambda: FailingChain()
    r = TestClient(app).post("/ask", json={"question": "hello?"})
    app.dependency_overrides.clear()
    assert r.status_code == 503


def test_upload_txt_success(client):
    text = b"Type 2 diabetes causes increased thirst and frequent urination. " * 20
    r = client.post("/upload", files={"file": ("notes.txt", text, "text/plain")})
    assert r.status_code == 200
    assert r.json()["filename"] == "notes.txt"
    assert r.json()["chunks"] >= 1


def test_upload_unsupported_type(client):
    r = client.post("/upload", files={"file": ("virus.exe", b"abc", "application/octet-stream")})
    assert r.status_code == 400


def test_upload_empty_file(client):
    r = client.post("/upload", files={"file": ("empty.txt", b"", "text/plain")})
    assert r.status_code == 400


def test_sources_endpoint(client):
    r = client.get("/sources", params={"question": "diabetes"})
    assert r.status_code == 200 and len(r.json()["sources"]) == 1


def test_stats_endpoint(client):
    assert client.get("/stats").json()["total_vector_count"] == 42

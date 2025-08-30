"""Tests for FastAPI web module."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, cast

import pytest
import yaml  # type: ignore[import-untyped]

pytest.importorskip("fastapi.testclient")

from fastapi.testclient import TestClient  # type: ignore[import-not-found]

from leropa import parser
from leropa.json_utils import json_dumps
from leropa.web import app

JSONDict = Dict[str, Any]


def _client() -> TestClient:
    """Return a test client for the web app."""

    # Create and return a test client for the FastAPI application.
    return TestClient(app)


def test_convert_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Endpoint should return parsed document data as JSON."""

    # Provide a fake implementation for ``fetch_document`` to avoid network.
    def fake_fetch(ver_id: str, cache_path: Path | None) -> JSONDict:
        return {"ver_id": ver_id}

    monkeypatch.setattr(parser, "fetch_document", fake_fetch)

    client = _client()
    response = client.get("/convert", params={"ver_id": "123"})

    # Ensure the mocked data is returned.
    assert response.status_code == 200
    assert response.json() == {"ver_id": "123"}


def test_chat_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chat form should display the generated answer."""

    class FakeModule:
        """Stub rag module used for tests."""

        @staticmethod
        def ask_with_context(
            question: str,
            collection: str,
            top_k: int = 24,
            final_k: int = 8,
            use_reranker: bool = True,
        ) -> JSONDict:
            return {"text": f"Echo: {question}", "contexts": []}

    # Replace the RAG helper with our stub implementation.
    monkeypatch.setattr(
        "leropa.web.routes.chat._RAG", FakeModule, raising=False
    )

    client = _client()
    response = client.post("/chat", data={"question": "Hi"})

    # Verify that the answer from the stub is present in the response.
    assert response.status_code == 200
    assert "Echo: Hi" in response.text


def test_models_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """/models should list available model names."""

    # Provide a deterministic set of models for the response.
    monkeypatch.setattr(
        "leropa.web.routes.models.available_models", lambda: ["m1", "m2"]
    )

    client = _client()
    response = client.get("/models")
    assert response.status_code == 200
    assert response.json() == ["m1", "m2"]


def test_root_page_links_documents() -> None:
    """Root page should link to the documents listing."""

    client = _client()
    response = client.get("/")
    assert response.status_code == 200
    assert '<a href="/documents?format=html"' in response.text


def test_root_page_has_citations_list() -> None:
    """Index page should include a container for citations."""

    client = _client()
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="citations"' in response.text


def test_chat_endpoint_uses_selected_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The chat endpoint should set the chosen LLM model."""

    class FakeRag:
        GEN_MODEL = ""

        @staticmethod
        def ask_with_context(
            question: str, collection: str, **_: object
        ) -> JSONDict:
            return {"text": f"Echo: {question}", "contexts": []}

    monkeypatch.setattr(
        "leropa.web.routes.chat.available_models", lambda: ["x"], raising=False
    )
    monkeypatch.setattr("leropa.web.routes.chat._RAG", FakeRag, raising=False)

    client = _client()
    response = client.post("/chat", data={"question": "Hi", "model": "x"})
    assert response.status_code == 200
    assert FakeRag.GEN_MODEL == "x"


def test_document_endpoints(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """List documents and fetch their structured content."""

    # Build two sample documents, one JSON and one YAML.
    doc1 = {
        "document": {
            "source": "s",
            "ver_id": "1",
            "title": "Doc1",
            "description": "",
            "keywords": "",
            "history": [],
            "prev_ver": None,
            "next_ver": None,
        },
        "articles": [
            {
                "article_id": "a1",
                "label": "1",
                "full_text": "P",
                "paragraphs": [
                    {
                        "par_id": "p1",
                        "text": "P",
                        "label": None,
                        "subparagraphs": [],
                        "notes": [],
                    }
                ],
                "notes": [],
            }
        ],
        "books": [],
        "annexes": [],
    }
    doc2 = cast(JSONDict, deepcopy(doc1))
    doc2_doc = cast(JSONDict, doc2["document"])
    doc2_doc["ver_id"] = "2"
    doc2_doc["title"] = "Doc2"

    # Write documents to disk in different formats.
    (tmp_path / "1.json").write_text(json_dumps(doc1))
    (tmp_path / "2.yaml").write_text(
        yaml.safe_dump(doc2, allow_unicode=True, sort_keys=False)
    )

    # Point the application to the temporary directory.
    monkeypatch.setenv("LEROPA_DOCUMENTS", str(tmp_path))

    client = _client()

    # Listing should include both documents.
    response = client.get("/documents")
    assert response.status_code == 200
    docs = response.json()
    assert {"ver_id": "1", "title": "Doc1"} in docs
    assert {"ver_id": "2", "title": "Doc2"} in docs

    # HTML listing should include both titles.
    response = client.get("/documents", params={"format": "html"})
    assert response.status_code == 200
    assert "Doc1" in response.text
    assert "Doc2" in response.text

    # Fetching a document should strip ``full_text``.
    response = client.get("/documents/1")
    assert response.status_code == 200
    data = response.json()
    assert "full_text" not in data["articles"][0]
    assert data["articles"][0]["paragraphs"][0]["text"] == "P"

    # HTML rendering should contain the article text.
    response = client.get("/documents/1", params={"format": "html"})
    assert response.status_code == 200
    assert "Doc1" in response.text


def test_document_admin_add_delete(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Adding and removing documents should interact with RAG helpers."""

    # Fake fetch_document returns structured content with one article.
    def fake_fetch(ver_id: str, cache_dir: Path | None = None) -> JSONDict:
        return {
            "document": {"ver_id": ver_id, "title": f"Doc{ver_id}"},
            "articles": [
                {
                    "article_id": f"a{ver_id}",
                    "label": "1",
                    "full_text": "T",
                    "paragraphs": [],
                    "notes": [],
                }
            ],
            "books": [],
            "annexes": [],
        }

    monkeypatch.setattr(parser, "fetch_document", fake_fetch)

    # Track RAG operations.
    calls: JSONDict = {"ingested": [], "deleted": []}

    class FakeRag:
        @staticmethod
        def ingest_folder(folder: str, collection: str) -> int:
            calls["ingested"].append(Path(folder))
            return 1

        @staticmethod
        def delete_by_article_id(article_id: str, collection: str) -> int:
            calls["deleted"].append(article_id)
            return 1

    monkeypatch.setattr(
        "leropa.web.routes.documents._RAG", FakeRag, raising=False
    )
    monkeypatch.setenv("LEROPA_DOCUMENTS", str(tmp_path))

    client = _client()

    # Adding should create file and ingest it.
    resp = client.post("/documents/add", json={"ver_id": "123"})
    assert resp.status_code == 200
    assert (tmp_path / "123.yaml").exists()
    assert calls["ingested"], "ingest_folder not called"

    # Deleting should move file and delete articles.
    resp = client.post("/documents/delete", json={"ids": ["123"]})
    assert resp.status_code == 200
    assert not (tmp_path / "123.yaml").exists()
    assert (tmp_path / "recycle" / "123.yaml").exists()
    assert calls["deleted"] == ["a123"]


def test_export_md_endpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Export endpoint should report counts from the exporter module."""

    class FakeModule:
        @staticmethod
        def export_folder(
            input_dir: str,
            output_dir: str,
            max_tokens: int,
            overlap_tokens: int,
            title_template: str,
            body_heading: str,
            ext: str,
        ) -> tuple[int, int]:
            return (1, 2)

    # Replace the exporter helper with our fake module.
    monkeypatch.setattr(
        "leropa.web.routes.export_md._EXPORTER", FakeModule, raising=False
    )

    client = _client()
    response = client.get(
        "/export-md",
        params={"input_dir": str(tmp_path), "output_dir": str(tmp_path)},
    )
    assert response.status_code == 200
    assert response.json() == {
        "articles": 1,
        "files": 2,
        "output_dir": str(tmp_path),
    }


def test_rag_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    """RAG routes should delegate to the imported module."""

    class FakeRag:
        @staticmethod
        def recreate_collection(collection: str, vector_size: int) -> None:
            pass

        @staticmethod
        def ingest_folder(
            folder: str,
            collection: str,
            batch_size: int,
            chunk_tokens: int,
            overlap_tokens: int,
        ) -> int:
            return 42

        @staticmethod
        def search(
            query: str,
            collection: str,
            top_k: int,
            label: str | None = None,
        ) -> list[dict[str, str]]:
            return [{"text": "hit"}]

        @staticmethod
        def ask_with_context(
            question: str,
            collection: str,
            top_k: int,
            final_k: int,
            use_reranker: bool,
        ) -> dict[str, object]:
            return {"text": "ans", "contexts": []}

        @staticmethod
        def delete_by_article_id(article_id: str, collection: str) -> int:
            return 3

        @staticmethod
        def start_qdrant_docker(
            name: str, port: int, volume: str, image: str
        ) -> bool:
            return True

    modules = [
        "leropa.web.routes.rag_recreate",
        "leropa.web.routes.rag_ingest",
        "leropa.web.routes.rag_search",
        "leropa.web.routes.rag_ask",
        "leropa.web.routes.rag_delete",
        "leropa.web.routes.rag_start_qdrant",
    ]
    for mod in modules:
        monkeypatch.setattr(mod, "_RAG", FakeRag, raising=False)

    client = _client()

    assert client.get("/rag/recreate").json()["status"] == "ready"
    assert (
        client.get("/rag/ingest", params={"folder": "."}).json()["chunks"]
        == 42
    )
    assert (
        client.get("/rag/search", params={"query": "q"}).json()[0]["text"]
        == "hit"
    )
    assert (
        client.post("/rag/search", json={"query": "q"}).json()[0]["text"]
        == "hit"
    )
    resp = client.get("/rag/ask", params={"question": "q"}).json()
    assert resp["text"] == "ans"
    assert resp["contexts"] == []
    resp = client.post("/rag/ask", json={"question": "q"}).json()
    assert resp["text"] == "ans"
    assert resp["contexts"] == []
    assert (
        client.delete("/rag/delete", params={"article_id": "a"}).json()[
            "deleted"
        ]
        == 3
    )
    assert client.get("/rag/start-qdrant").json()["started"] is True

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

    # Replace the module loader with our stub implementation.
    monkeypatch.setattr(
        "leropa.web._import_llm_module", lambda name: FakeModule, raising=False
    )

    client = _client()
    response = client.post("/chat", data={"question": "Hi"})

    # Verify that the answer from the stub is present in the response.
    assert response.status_code == 200
    assert "Echo: Hi" in response.text


def test_models_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """/models should list available model names."""

    # Provide a deterministic set of models for the response.
    monkeypatch.setattr("leropa.web.available_models", lambda: ["m1", "m2"])

    client = _client()
    response = client.get("/models")
    assert response.status_code == 200
    assert response.json() == ["m1", "m2"]


def test_chat_form_lists_models(monkeypatch: pytest.MonkeyPatch) -> None:
    """The chat form should offer model choices."""

    monkeypatch.setattr("leropa.web.available_models", lambda: ["m1", "m2"])
    client = _client()
    response = client.get("/")
    assert response.status_code == 200
    assert "<option value='m1'>" in response.text
    assert "<option value='m2'>" in response.text


def test_chat_endpoint_uses_selected_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The chat endpoint should import the chosen model."""

    class FakeModule:
        @staticmethod
        def ask_with_context(
            question: str, collection: str, **_: object
        ) -> JSONDict:
            return {"text": f"Echo: {question}", "contexts": []}

    imported: dict[str, str] = {}

    def fake_loader(name: str) -> type[FakeModule]:
        imported["name"] = name
        return FakeModule

    monkeypatch.setattr(
        "leropa.web._import_llm_module", fake_loader, raising=False
    )
    monkeypatch.setattr("leropa.web.available_models", lambda: ["x"])

    client = _client()
    response = client.post("/chat", data={"question": "Hi", "model": "x"})
    assert response.status_code == 200
    assert imported["name"] == "x"


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

    # Fetching a document should strip ``full_text``.
    response = client.get("/documents/1")
    assert response.status_code == 200
    data = response.json()
    assert "full_text" not in data["articles"][0]
    assert data["articles"][0]["paragraphs"][0]["text"] == "P"

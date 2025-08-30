"""Tests for FastAPI web module."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from leropa import parser
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
            question: str, collection: str, **_: Any
        ) -> JSONDict:
            return {"text": f"Echo: {question}", "contexts": []}

    imported: dict[str, str] = {}

    def fake_loader(name: str) -> Any:
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

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

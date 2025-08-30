"""Tests for the LLM utilities."""

from types import SimpleNamespace

import pytest
import requests  # type: ignore[import-untyped]

from leropa.llm import available_models


def test_available_models_queries_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure available_models returns sorted names from the server."""

    def fake_get(url: str, timeout: int = 5) -> SimpleNamespace:
        return SimpleNamespace(
            json=lambda: {"models": [{"name": "b"}, {"name": "a"}]},
            raise_for_status=lambda: None,
        )

    monkeypatch.setattr(requests, "get", fake_get)
    assert available_models() == ["a", "b"]


def test_available_models_handles_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure available_models returns an empty list on failure."""

    def fake_get(*_: object, **__: object) -> SimpleNamespace:
        raise requests.RequestException("fail")

    monkeypatch.setattr(requests, "get", fake_get)
    assert available_models() == []

"""Tests for document caching and metadata inclusion."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml  # type: ignore[import-untyped]

from leropa import document_cache

JSONDict = Dict[str, Any]


def _sample_doc(ver_id: str) -> JSONDict:
    """Return a minimal structured document for tests."""
    return {
        "document": {
            "source": "s",
            "ver_id": ver_id,
            "title": "T",
            "description": "",
            "keywords": "",
            "history": [],
            "prev_ver": None,
            "next_ver": None,
        },
        "articles": [],
        "books": [],
        "annexes": [],
    }


def test_load_document_info_caches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Repeated calls should reuse cached ``DocumentInfo`` instances."""
    path = tmp_path / "1.yaml"

    # Prepare fake loader to count invocations.
    doc = _sample_doc("1")
    calls = {"count": 0}

    def fake_loader(p: Path) -> JSONDict:
        calls["count"] += 1
        return doc

    monkeypatch.setattr(document_cache, "_load_document_file", fake_loader)

    # First call parses and caches.
    info1 = document_cache.load_document_info(path)
    assert calls["count"] == 1

    # Second call should hit cache.
    info2 = document_cache.load_document_info(path)
    assert calls["count"] == 1
    assert info1 is info2

    # Expire cache and ensure reload.
    document_cache._CACHE[path] = (0.0, info1)
    document_cache.load_document_info(path)
    assert calls["count"] == 2


def test_ask_with_context_includes_document_info(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """ask_with_context should reference ``DocumentInfo`` once per file."""
    rag = pytest.importorskip("leropa.llm.rag_legal_qdrant")

    doc_path = tmp_path / "1.yaml"
    doc_path.write_text(
        yaml.safe_dump(_sample_doc("1"), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    # Ensure helper uses temporary documents directory.
    monkeypatch.setattr(rag, "DOCUMENTS_DIR", tmp_path)

    # Stub search and chat helpers to avoid external services.
    def fake_search(
        question: str, collection: str, top_k: int
    ) -> list[dict[str, Any]]:
        return [
            {
                "text": "A",
                "source_file": str(doc_path),
                "article_id": "a1",
                "label": "1",
                "score": 0.1,
                "rerank": 0.1,
            },
            {
                "text": "B",
                "source_file": str(doc_path),
                "article_id": "a2",
                "label": "2",
                "score": 0.2,
                "rerank": 0.2,
            },
        ]

    monkeypatch.setattr(rag, "search", fake_search)
    monkeypatch.setattr(rag, "_ollama_chat", lambda s, u, stream=False: "ans")

    result = rag.ask_with_context(
        "Q", collection="c", top_k=2, final_k=2, use_reranker=False
    )

    assert result["documents"]["1"]["title"] == "T"
    assert len(result["documents"]) == 1

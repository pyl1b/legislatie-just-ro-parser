"""Perform a semantic search over ingested articles."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module

router = APIRouter()


@router.get("/rag/search")
async def rag_search(
    query: str,
    collection: str = "legal_articles",
    topk: int = 24,
    label: str | None = None,
    model: str = "rag_legal_qdrant",
) -> JSONResponse:
    """Perform a semantic search over ingested articles.

    Args:
        query: Query string for semantic search.
        collection: Qdrant collection name.
        topk: Number of results to retrieve.
        label: Filter by article label.

    Returns:
        Search results from the RAG module.
    """

    # Import the requested RAG module and perform the search.
    mod = _import_llm_module(model)
    hits = mod.search(query, collection=collection, top_k=topk, label=label)
    return JSONResponse(hits)

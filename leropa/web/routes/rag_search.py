"""Perform a semantic search over ingested articles."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]
from pydantic import BaseModel  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module

router = APIRouter()


class SearchRequest(BaseModel):
    """Input payload for the search endpoint."""

    query: str
    collection: str = "legal_articles"
    topk: int = 24
    label: str | None = None


# Load the RAG module once; used for search operations.
_RAG = _import_llm_module("rag_legal_qdrant")


@router.get("/rag/search")
async def rag_search_get(
    query: str,
    collection: str = "legal_articles",
    topk: int = 24,
    label: str | None = None,
) -> JSONResponse:
    """Perform a semantic search over ingested articles via query params.

    Args:
        query: Text to search for.
        collection: Qdrant collection name.
        topk: Number of results to return.
        label: Optional article label filter.

    Returns:
        Search results from the RAG module.
    """

    hits = _RAG.search(
        query,
        collection=collection,
        top_k=topk,
        label=label,
    )
    return JSONResponse(hits)


@router.post("/rag/search")
async def rag_search_post(payload: SearchRequest) -> JSONResponse:
    """Perform a semantic search over ingested articles via JSON body.

    Args:
        payload: Parameters controlling the search.

    Returns:
        Search results from the RAG module.
    """

    hits = _RAG.search(
        payload.query,
        collection=payload.collection,
        top_k=payload.topk,
        filter_by_label=payload.label,
    )
    return JSONResponse(hits)

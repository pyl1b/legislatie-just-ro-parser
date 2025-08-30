"""Delete items from the collection by ``article_id``."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module

router = APIRouter()

# Load the RAG module once for collection operations.
_RAG = _import_llm_module("rag_legal_qdrant")


@router.delete("/rag/delete")
async def rag_delete(
    article_id: str,
    collection: str = "legal_articles",
) -> JSONResponse:
    """Delete items from the collection by ``article_id``.

    Args:
        article_id: Identifier of the article to remove.
        collection: Qdrant collection name.

    Returns:
        Number of deleted points.
    """

    # Perform the deletion using the RAG helper.
    total_deleted = _RAG.delete_by_article_id(
        article_id, collection=collection
    )
    return JSONResponse({"deleted": total_deleted})

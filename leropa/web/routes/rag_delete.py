"""Delete items from the collection by ``article_id``."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module

router = APIRouter()


@router.delete("/rag/delete")
async def rag_delete(
    article_id: str,
    collection: str = "legal_articles",
    model: str = "rag_legal_qdrant",
) -> JSONResponse:
    """Delete items from the collection by ``article_id``.

    Args:
        article_id: Identifier of the article to remove.
        collection: Qdrant collection name.

    Returns:
        Number of deleted points.
    """

    # Import the requested RAG module and perform the deletion.
    mod = _import_llm_module(model)
    total_deleted = mod.delete_by_article_id(article_id, collection=collection)
    return JSONResponse({"deleted": total_deleted})

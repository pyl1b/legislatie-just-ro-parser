"""(Re)create the configured Qdrant collection."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module

router = APIRouter()


@router.get("/rag/recreate")
async def rag_recreate(
    collection: str = "legal_articles",
    dims: int = 768,
    model: str = "rag_legal_qdrant",
) -> JSONResponse:
    """(Re)create the configured Qdrant collection.

    Args:
        collection: Qdrant collection name.
        dims: Embedding vector size.

    Returns:
        Confirmation of the operation.
    """

    # Import the requested RAG module and trigger the collection creation.
    mod = _import_llm_module(model)
    mod.recreate_collection(collection, vector_size=dims)
    return JSONResponse({"status": "ready"})

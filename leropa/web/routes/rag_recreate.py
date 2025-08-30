"""(Re)create the configured Qdrant collection."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module
from leropa.web.utils import DOCUMENTS_DIR

router = APIRouter()

# Load the RAG module once for collection maintenance.
_RAG = _import_llm_module("rag_legal_qdrant")


@router.get("/rag/recreate")
async def rag_recreate(
    collection: str = "legal_articles",
    dims: int = 768,
) -> JSONResponse:
    """(Re)create the configured Qdrant collection.

    Args:
        collection: Qdrant collection name.
        dims: Embedding vector size.

    Returns:
        Confirmation of the operation.
    """

    # Trigger the collection creation using the RAG helper.
    _RAG.recreate_collection(collection, vector_size=dims)
    _RAG.ingest_folder(
        str(DOCUMENTS_DIR),
        collection=collection,
        batch_size=32,
        chunk_tokens=1000,
        overlap_tokens=200,
    )
    return JSONResponse({"status": "ready"})

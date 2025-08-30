"""Ingest a folder of JSON/JSONL files."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module

router = APIRouter()

# Load the RAG module once; used for ingestion operations.
_RAG = _import_llm_module("rag_legal_qdrant")


@router.get("/rag/ingest")
async def rag_ingest(
    folder: str,
    collection: str = "legal_articles",
    batch: int = 32,
    chunk: int = 1000,
    overlap: int = 200,
) -> JSONResponse:
    """Ingest a folder of JSON/JSONL files.

    Args:
        folder: Path to the directory containing the data files.
        collection: Qdrant collection name.
        batch: Batch size for uploads.
        chunk: Tokens per chunk.
        overlap: Token overlap between chunks.

    Returns:
        Number of ingested chunks.
    """

    # Process the folder using the RAG helper.
    total_ingested = _RAG.ingest_folder(
        folder,
        collection=collection,
        batch_size=batch,
        chunk_tokens=chunk,
        overlap_tokens=overlap,
    )
    return JSONResponse({"chunks": total_ingested})

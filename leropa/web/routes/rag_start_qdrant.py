"""Attempt to start Qdrant via Docker."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module

router = APIRouter()

# Load the RAG module once; used for utility operations.
_RAG = _import_llm_module("rag_legal_qdrant")


@router.get("/rag/start-qdrant")
async def rag_start_qdrant(
    name: str = "qdrant",
    port: int = 6333,
    volume: str = "qdrant_storage",
    image: str = "qdrant/qdrant:latest",
) -> JSONResponse:
    """Attempt to start Qdrant via Docker.

    Args:
        name: Docker container name.
        port: Qdrant port to expose.
        volume: Docker volume for persistent storage.
        image: Docker image to run.

    Returns:
        Whether the container was started successfully.
    """

    # Start the Docker container using the RAG helper.
    result = _RAG.start_qdrant_docker(
        name=name, port=port, volume=volume, image=image
    )
    return JSONResponse({"started": bool(result)})

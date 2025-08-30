"""Attempt to start Qdrant via Docker."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module

router = APIRouter()


@router.get("/rag/start-qdrant")
async def rag_start_qdrant(
    name: str = "qdrant",
    port: int = 6333,
    volume: str = "qdrant_storage",
    image: str = "qdrant/qdrant:latest",
    model: str = "rag_legal_qdrant",
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

    # Import the requested RAG module and start the Docker container.
    mod = _import_llm_module(model)
    result = mod.start_qdrant_docker(
        name=name, port=port, volume=volume, image=image
    )
    return JSONResponse({"started": bool(result)})

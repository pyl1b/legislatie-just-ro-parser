"""Model listing route."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from leropa.llm import available_models

router = APIRouter()


@router.get("/models")
async def list_models() -> JSONResponse:
    """Return the list of available LLM models."""

    # Provide the model names as a simple JSON list.
    return JSONResponse(available_models())

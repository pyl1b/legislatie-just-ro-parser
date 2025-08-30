"""Root page displaying a chat form."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import HTMLResponse  # type: ignore[import-not-found]

from leropa.llm import available_models

router = APIRouter()


@router.get("/")
async def chat_form() -> HTMLResponse:
    """Render a minimal chat form."""

    # Build options for all available models.
    model_opts = "".join(
        f"<option value='{name}'>{name}</option>"
        for name in available_models()
    )

    # Return a simple HTML form for submitting questions and selecting a model.
    return HTMLResponse(
        "<form method='post' action='/chat'>"
        f"<select name='model'>{model_opts}</select>"
        "<input name='question' type='text'/>"
        "<button type='submit'>Ask</button>"
        "</form>"
    )

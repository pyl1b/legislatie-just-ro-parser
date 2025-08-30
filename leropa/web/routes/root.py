"""Root page displaying the RAG interface."""

from __future__ import annotations

from fastapi import APIRouter, Request  # type: ignore[import-not-found]
from fastapi.responses import HTMLResponse  # type: ignore[import-not-found]

from ..utils import templates

router = APIRouter()


@router.get("/")
async def root_page(request: Request) -> HTMLResponse:
    """Render the main page with chat and search forms.

    Args:
        request: Incoming request used for template rendering.

    Returns:
        Rendered HTML page.
    """

    # Render the Jinja2 template for the main page.
    return templates.TemplateResponse("index.html", {"request": request})

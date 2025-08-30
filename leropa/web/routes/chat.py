"""Chat endpoint for interacting with RAG models."""

from __future__ import annotations

from fastapi import APIRouter, Form  # type: ignore[import-not-found]
from fastapi.responses import HTMLResponse  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module
from leropa.llm import available_models

router = APIRouter()


@router.post("/chat")
async def chat(
    question: str = Form(...),
    model: str = Form("rag_legal_qdrant"),
) -> HTMLResponse:
    """Handle chat questions and display the answer."""

    # Import the requested RAG module and generate an answer.
    mod = _import_llm_module(model)
    answer = mod.ask_with_context(question, collection="legal_articles")

    # Build the model options for rendering the form again.
    model_opts = "".join(
        f"<option value='{name}'>{name}</option>"
        for name in available_models()
    )

    # Render the answer in a new HTML page along with the form.
    return HTMLResponse(
        f"<p>{answer['text']}</p>"
        "<form method='post' action='/chat'>"
        f"<select name='model'>{model_opts}</select>"
        "<input name='question' type='text'/>"
        "<button type='submit'>Ask</button>"
        "</form>"
    )

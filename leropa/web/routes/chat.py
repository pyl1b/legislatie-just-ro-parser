"""Chat endpoint for interacting with RAG models."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Form  # type: ignore[import-not-found]
from fastapi.responses import HTMLResponse  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module
from leropa.llm import available_models

from ..utils import get_translator

router = APIRouter()

# Load the RAG module once; it provides the ``ask_with_context`` helper.
_RAG: Any = _import_llm_module("rag_legal_qdrant")


@router.post("/chat")
async def chat(
    question: str = Form(...),
    model: str = Form("llama3.2:3b"),
    lang: Literal["en", "ro"] = "en",
) -> HTMLResponse:
    """Handle chat questions and display the answer."""

    # Configure the generation model on the RAG helper and generate an answer.
    setattr(_RAG, "GEN_MODEL", model)
    answer = _RAG.ask_with_context(
        question, collection="legal_articles", language=lang
    )

    # Build the model options for rendering the form again, marking selection.
    model_opts = "".join(
        f"<option value='{name}'"
        f"{' selected' if name == model else ''}>{name}</option>"
        for name in available_models()
    )

    tr = get_translator(lang)
    # Render the answer in a new HTML page along with the form.
    return HTMLResponse(
        f"<p>{answer['text']}</p>"
        f"<form method='post' action='/chat?lang={lang}'>"
        f"<select name='model'>{model_opts}</select>"
        "<input name='question' type='text'/>"
        f"<button type='submit'>{tr('ask_button', 'Ask')}</button>"
        "</form>"
    )

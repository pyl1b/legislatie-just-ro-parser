"""Ask a question and receive an answer with context."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]
from pydantic import BaseModel  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module

router = APIRouter()


class AskRequest(BaseModel):
    """Input payload for the ask endpoint."""

    question: str
    collection: str = "legal_articles"
    topk: int = 24
    finalk: int = 8
    no_rerank: bool = False


# Load the RAG module once; used for answering questions.
_RAG = _import_llm_module("rag_legal_qdrant")


@router.api_route("/rag/ask", methods=["GET", "POST"])
async def rag_ask(payload: AskRequest) -> JSONResponse:
    """Ask a question and receive an answer with context.

    Args:
        payload: Parameters controlling the question and retrieval.

    Returns:
        Generated answer and its contexts.
    """

    # Get the answer with context using the RAG helper.
    answer = _RAG.ask_with_context(
        payload.question,
        collection=payload.collection,
        top_k=payload.topk,
        final_k=payload.finalk,
        use_reranker=not payload.no_rerank,
    )
    return JSONResponse(answer)

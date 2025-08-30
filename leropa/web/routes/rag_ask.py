"""Ask a question and receive an answer with context."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module

router = APIRouter()


@router.get("/rag/ask")
async def rag_ask(
    question: str,
    collection: str = "legal_articles",
    topk: int = 24,
    finalk: int = 8,
    no_rerank: bool = False,
    model: str = "rag_legal_qdrant",
) -> JSONResponse:
    """Ask a question and receive an answer with context.

    Args:
        question: The question to ask the model.
        collection: Qdrant collection name.
        topk: Number of documents to retrieve.
        finalk: Number of documents to include in the final context.
        no_rerank: Disable the re-ranker when True.

    Returns:
        Generated answer and its contexts.
    """

    # Import the requested RAG module and get the answer with context.
    mod = _import_llm_module(model)
    answer = mod.ask_with_context(
        question,
        collection=collection,
        top_k=topk,
        final_k=finalk,
        use_reranker=not no_rerank,
    )
    return JSONResponse(answer)

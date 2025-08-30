"""Ask a question and receive an answer with context."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]
from pydantic import BaseModel  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module

router = APIRouter()


class AskRequest(BaseModel):
    """Input payload for the ask endpoint.

    Attributes:
        question: The question to ask the model.
        collection: Qdrant collection name.
        topk: Number of documents to retrieve.
        finalk: Number of documents to include in final context.
        no_rerank: Disable the re-ranker when true.
        model: Name of the LLM model to use.
    """

    question: str
    collection: str = "legal_articles"
    topk: int = 24
    finalk: int = 8
    no_rerank: bool = False
    model: str | None = None


# Load the RAG module once; used for answering questions.
_RAG = _import_llm_module("rag_legal_qdrant")


@router.get("/rag/ask")
async def rag_ask_get(
    question: str,
    collection: str = "legal_articles",
    topk: int = 24,
    finalk: int = 8,
    no_rerank: bool = False,
    model: str | None = None,
) -> JSONResponse:
    """Ask a question via query parameters and receive an answer.

    Args:
        question: The question to ask the model.
        collection: Qdrant collection name.
        topk: Number of documents to retrieve.
        finalk: Number of documents to include in final context.
        no_rerank: Disable the re-ranker when true.
        model: Name of the LLM model to use.

    Returns:
        Generated answer and its contexts.
    """

    if model:
        setattr(_RAG, "GEN_MODEL", model)

    answer = _RAG.ask_with_context(
        question,
        collection=collection,
        top_k=topk,
        final_k=finalk,
        use_reranker=not no_rerank,
    )
    return JSONResponse(answer)


@router.post("/rag/ask")
async def rag_ask_post(payload: AskRequest) -> JSONResponse:
    """Ask a question via JSON body and receive an answer.

    Args:
        payload: Parameters controlling the question and retrieval.

    Returns:
        Generated answer and its contexts.
    """

    if payload.model:
        setattr(_RAG, "GEN_MODEL", payload.model)

    answer = _RAG.ask_with_context(
        payload.question,
        collection=payload.collection,
        top_k=payload.topk,
        final_k=payload.finalk,
        use_reranker=not payload.no_rerank,
    )
    return JSONResponse(answer)

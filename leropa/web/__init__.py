"""FastAPI application exposing CLI commands."""

from __future__ import annotations

from fastapi import FastAPI  # type: ignore[import-not-found]

# Import routers from individual route modules and register them with the app.
from .routes import (
    chat,
    convert,
    document_detail,
    documents,
    export_md,
    models,
    rag_ask,
    rag_delete,
    rag_ingest,
    rag_recreate,
    rag_search,
    rag_start_qdrant,
    root,
)

# Create the main FastAPI application and include all routers.
app = FastAPI()

app.include_router(models.router)
app.include_router(root.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(document_detail.router)
app.include_router(convert.router)
app.include_router(export_md.router)
app.include_router(rag_recreate.router)
app.include_router(rag_ingest.router)
app.include_router(rag_search.router)
app.include_router(rag_ask.router)
app.include_router(rag_delete.router)
app.include_router(rag_start_qdrant.router)

__all__ = ["app"]

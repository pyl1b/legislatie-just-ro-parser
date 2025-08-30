"""List structured documents available on the server."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from fastapi import (  # type: ignore[import-not-found]
    APIRouter,
    Query,
    Request,
    Response,
)
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]
from pydantic import BaseModel  # type: ignore[import-not-found]

from leropa import parser
from leropa.cli import _import_llm_module
from leropa.document_cache import load_document_info

from ..utils import (
    DOCUMENTS_DIR,
    DocumentSummaryList,
    create_jinja_context,
    document_files,
    get_documents_dir,
    load_document_file,
    templates,
)

_RAG = _import_llm_module("rag_legal_qdrant")

RECYCLE_DIR = DOCUMENTS_DIR / "recycle"

router = APIRouter()


def _load_summaries() -> DocumentSummaryList:
    """Return summaries for available structured documents.

    Returns:
        List of mappings containing document identifiers and titles.
    """

    summaries: DocumentSummaryList = []

    # Iterate through all known document files.
    for path in document_files():
        # Use the same metadata cache employed by RAG operations.
        info = load_document_info(path)

        # Record identifier and title for later rendering.
        summaries.append({"ver_id": info.ver_id, "title": info.title})

    return summaries


@router.get("/documents")
async def list_documents(
    request: Request,
    format: str = Query(default="json", enum=["json", "html"]),
) -> Response:
    """List structured documents available on the server.

    Args:
        request: Incoming request used for template rendering.
        format: Desired response format.

    Returns:
        Either a JSON list or an HTML page with document links.
    """

    # Gather summaries using the shared metadata cache.
    summaries = _load_summaries()

    # Render as HTML when requested.
    if format == "html":
        return templates.TemplateResponse(
            "documents.html",
            context=create_jinja_context(
                request=request,
                documents=summaries,
                title="Documents | leropa",
            ),
        )

    return JSONResponse(summaries)


@router.post("/documents")
async def list_documents_raw() -> JSONResponse:
    """Return raw list of document identifiers and titles.

    Returns:
        List of document summaries.
    """

    # Return collected summaries as JSON.
    return JSONResponse(_load_summaries())


@router.get("/documents-admin")
async def documents_admin(request: Request) -> Response:
    """Render admin page for adding and deleting documents.

    Args:
        request: Incoming request used for template rendering.

    Returns:
        Rendered HTML response containing management controls.
    """

    summaries = _load_summaries()
    return templates.TemplateResponse(
        "documents_admin.html",
        context=create_jinja_context(
            request=request,
            documents=summaries,
            title="Documents Admin | leropa",
        ),
    )


@router.post("/documents/add")
async def add_document(payload: "AddRequest") -> JSONResponse:
    """Fetch, save and ingest a new document.

    Args:
        payload: Request payload containing the document identifier.

    Returns:
        Summary information about the stored document.
    """

    # Parse the document from the remote source.
    doc = parser.fetch_document(payload.ver_id, cache_dir=None)

    # Ensure the documents directory exists and write the YAML dump.
    docs_dir = get_documents_dir()
    docs_dir.mkdir(parents=True, exist_ok=True)
    target = docs_dir / f"{payload.ver_id}.yaml"
    target.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    # Ingest only the newly created file by copying it into a temp folder.
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy2(target, Path(tmp) / target.name)
        _RAG.ingest_folder(tmp, collection="legal_articles")

    info = doc.get("document", {})
    return JSONResponse(
        {"ver_id": info.get("ver_id"), "title": info.get("title")}
    )


@router.post("/documents/delete")
async def delete_documents(payload: "DeleteRequest") -> JSONResponse:
    """Remove documents and delete their articles from the database.

    Args:
        payload: Request payload containing document identifiers to remove.

    Returns:
        Mapping containing the removed identifiers.
    """

    removed: list[str] = []
    recycle_dir = get_documents_dir() / "recycle"
    recycle_dir.mkdir(parents=True, exist_ok=True)

    # Iterate over requested identifiers.
    for ver_id in payload.ids:
        # Locate a matching document file.
        path = next((p for p in document_files() if p.stem == ver_id), None)
        if not path:
            continue

        # Load the document to extract article identifiers.
        data = load_document_file(path)
        for article in data.get("articles", []):
            art_id = article.get("article_id")
            if art_id:
                _RAG.delete_by_article_id(art_id, collection="legal_articles")

        # Move the file into the recycle bin.
        shutil.move(str(path), recycle_dir / path.name)
        removed.append(ver_id)

    return JSONResponse({"removed": removed})


class AddRequest(BaseModel):
    """Request body for adding a document."""

    ver_id: str


class DeleteRequest(BaseModel):
    """Request body for deleting documents."""

    ids: list[str]

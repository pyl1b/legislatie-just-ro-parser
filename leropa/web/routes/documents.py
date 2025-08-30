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

from leropa import parser
from leropa.cli import _import_llm_module

from ..utils import (
    DOCUMENTS_DIR,
    DocumentSummaryList,
    create_jinja_context,
    document_files,
    load_document_file,
    templates,
)

_RAG = _import_llm_module("rag_legal_qdrant")

RECYCLE_DIR = DOCUMENTS_DIR / "recycle"

router = APIRouter()


@router.get("/documents")
async def list_documents(
    request: Request,
    format: str = Query(default="html", enum=["json", "html"]),
) -> Response:
    """List structured documents available on the server.

    Args:
        request: Incoming request used for template rendering.
        format: Desired response format.

    Returns:
        Either a JSON list or an HTML page with document links.
    """

    # Gather summaries for all known documents.
    summaries: DocumentSummaryList = []
    for path in document_files():
        data = load_document_file(path)
        info = data.get("document", {})
        summaries.append(
            {"ver_id": info.get("ver_id"), "title": info.get("title")}
        )

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

    # Initialize list for summary entries.
    summaries: DocumentSummaryList = []

    # Iterate through all known document files.
    for path in document_files():
        # Read document structure from disk.
        data = load_document_file(path)
        info = data.get("document", {})

        # Record identifier and title.
        summaries.append(
            {"ver_id": info.get("ver_id"), "title": info.get("title")}
        )

    # Return collected summaries as JSON.
    return JSONResponse(summaries)


@router.post("/documents/add")
async def add_document(ver_id: str) -> JSONResponse:
    """Fetch, save and ingest a new document.

    Args:
        ver_id: Identifier of the document to add.

    Returns:
        Summary information about the stored document.
    """

    # Parse the document from the remote source.
    doc = parser.fetch_document(ver_id, cache_dir=None)

    # Ensure the documents directory exists and write the YAML dump.
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    target = DOCUMENTS_DIR / f"{ver_id}.yaml"
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
async def delete_documents(ids: list[str]) -> JSONResponse:
    """Remove documents and delete their articles from the database.

    Args:
        ids: List of document identifiers to remove.

    Returns:
        Mapping containing the removed identifiers.
    """

    removed: list[str] = []
    RECYCLE_DIR.mkdir(parents=True, exist_ok=True)

    # Iterate over requested identifiers.
    for ver_id in ids:
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
        shutil.move(str(path), RECYCLE_DIR / path.name)
        removed.append(ver_id)

    return JSONResponse({"removed": removed})

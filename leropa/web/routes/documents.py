"""List structured documents available on the server."""

from __future__ import annotations

from fastapi import (  # type: ignore[import-not-found]
    APIRouter,
    Query,
    Request,
    Response,
)
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from ..utils import (
    DocumentSummaryList,
    _document_files,
    _load_document_file,
    templates,
)

router = APIRouter()


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

    # Gather summaries for all known documents.
    summaries: DocumentSummaryList = []
    for path in _document_files():
        data = _load_document_file(path)
        info = data.get("document", {})
        summaries.append(
            {"ver_id": info.get("ver_id"), "title": info.get("title")}
        )

    # Render as HTML when requested.
    if format == "html":
        return templates.TemplateResponse(
            "documents.html", {"request": request, "documents": summaries}
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
    for path in _document_files():
        # Read document structure from disk.
        data = _load_document_file(path)
        info = data.get("document", {})

        # Record identifier and title.
        summaries.append(
            {"ver_id": info.get("ver_id"), "title": info.get("title")}
        )

    # Return collected summaries as JSON.
    return JSONResponse(summaries)

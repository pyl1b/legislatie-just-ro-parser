"""Fetch a specific structured document."""

from __future__ import annotations

from fastapi import (  # type: ignore[import-not-found]
    APIRouter,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from ..utils import (
    _document_files,
    _load_document_file,
    _strip_full_text,
    templates,
)

router = APIRouter()


@router.get("/documents/{ver_id}")
async def get_document(
    ver_id: str,
    request: Request,
    format: str = Query(default="json", enum=["json", "html"]),
) -> Response:
    """Return a specific document by version identifier.

    Args:
        ver_id: Document version identifier.
        request: Incoming request used for template rendering.
        format: Desired response format.

    Returns:
        Document structure without ``full_text`` fields or its HTML rendering.
    """

    # Locate the document file matching ``ver_id``.
    file_path = next((p for p in _document_files() if p.stem == ver_id), None)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = _strip_full_text(_load_document_file(file_path))

    # Render as HTML when requested.
    if format == "html":
        return templates.TemplateResponse(
            "document_detail.html", {"request": request, "doc": doc}
        )

    return JSONResponse(doc)

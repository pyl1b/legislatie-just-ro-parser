"""Fetch a specific structured document."""

from __future__ import annotations

from fastapi import (  # type: ignore[import-not-found]
    APIRouter,
    HTTPException,
    Query,
    Response,
)
from fastapi.responses import (  # type: ignore[import-not-found]
    HTMLResponse,
    JSONResponse,
)

from ..utils import (
    _document_files,
    _load_document_file,
    _render_document,
    _strip_full_text,
)

router = APIRouter()


@router.get("/documents/{ver_id}")
async def get_document(
    ver_id: str,
    format: str = Query(default="json", enum=["json", "html"]),
) -> Response:
    """Return a specific document by version identifier.

    Args:
        ver_id: Document version identifier.
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
        return HTMLResponse(_render_document(doc))

    return JSONResponse(doc)

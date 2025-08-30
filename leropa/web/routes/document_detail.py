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
    create_jinja_context,
    document_files,
    load_document_file,
    strip_full_text,
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
    file_path = next((p for p in document_files() if p.stem == ver_id), None)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = strip_full_text(load_document_file(file_path))

    # Render as HTML when requested.
    if format == "html":
        return templates.TemplateResponse(
            "document_detail.html",
            context=create_jinja_context(request=request, doc=doc),
        )

    return JSONResponse(doc)


@router.post("/documents/{ver_id}")
async def get_document_raw(ver_id: str) -> Response:
    """Return the raw content of a document file.

    Args:
        ver_id: Document version identifier.

    Returns:
        Raw text of the document's JSON or YAML file.
    """

    # Locate the document file matching ``ver_id``.
    file_path = next((p for p in document_files() if p.stem == ver_id), None)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Document not found")

    # Read the file contents as text.
    text = file_path.read_text(encoding="utf-8")

    # Choose response media type based on file extension.
    media_type = (
        "application/json"
        if file_path.suffix == ".json"
        else "application/x-yaml"
    )

    # Return the raw document text.
    return Response(content=text, media_type=media_type)

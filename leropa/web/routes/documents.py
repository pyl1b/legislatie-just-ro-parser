"""List structured documents available on the server."""

from __future__ import annotations

from fastapi import (  # type: ignore[import-not-found]
    APIRouter,
    Query,
    Response,
)
from fastapi.responses import (  # type: ignore[import-not-found]
    HTMLResponse,
    JSONResponse,
)

from ..utils import DocumentSummaryList, _document_files, _load_document_file

router = APIRouter()


@router.get("/documents")
async def list_documents(
    format: str = Query(default="json", enum=["json", "html"]),
) -> Response:
    """List structured documents available on the server.

    Args:
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
        template = (
            "<li><a href='/documents/{ver}?format=html'>{title}</a></li>"
        )
        items = "".join(
            template.format(ver=s["ver_id"], title=s["title"])
            for s in summaries
        )
        return HTMLResponse(f"<ul>{items}</ul>")

    return JSONResponse(summaries)

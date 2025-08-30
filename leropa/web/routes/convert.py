"""Convert a document identifier to structured data."""

from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import yaml  # type: ignore[import-untyped]
from fastapi import (  # type: ignore[import-not-found]
    APIRouter,
    BackgroundTasks,
    Query,
    Response,
)
from fastapi.responses import (  # type: ignore[import-not-found]
    FileResponse,
    JSONResponse,
    PlainTextResponse,
)

from leropa import parser
from leropa.xlsx import write_workbook

router = APIRouter()


@router.get("/convert")
async def convert_endpoint(
    ver_id: str,
    background_tasks: BackgroundTasks,
    cache_dir: str | None = Query(default=None),
    output_format: str = Query(default="json", enum=["json", "yaml", "xlsx"]),
) -> Response:
    """Convert a document identifier to structured data.

    Args:
        ver_id: Identifier for the document version to convert.
        cache_dir: Directory for the HTML cache.
        output_format: Desired output format.

    Returns:
        The structured document in the requested format.
    """

    # Convert cache path to ``Path`` if provided.
    cache_path = Path(cache_dir) if cache_dir else None

    # Retrieve and parse the document structure.
    doc = parser.fetch_document(ver_id, cache_path)

    # Return JSON when requested.
    if output_format == "json":
        return JSONResponse(doc)

    # Return YAML output.
    if output_format == "yaml":
        text = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)
        return PlainTextResponse(text, media_type="application/x-yaml")

    # Prepare XLSX output by writing to a temporary file.
    tmp = NamedTemporaryFile(suffix=".xlsx", delete=False)
    write_workbook(doc, Path(tmp.name))

    # Schedule file deletion after the response is sent.
    background_tasks.add_task(os.unlink, tmp.name)

    # Serve the file as a download.
    return FileResponse(tmp.name, filename=f"{ver_id}.xlsx")

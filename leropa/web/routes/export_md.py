"""Export legal JSON articles to chunked Markdown files."""

from __future__ import annotations

from fastapi import APIRouter  # type: ignore[import-not-found]
from fastapi.responses import JSONResponse  # type: ignore[import-not-found]

from leropa.cli import _import_llm_module

router = APIRouter()

# Load the exporter module once; it exposes ``export_folder``.
_EXPORTER = _import_llm_module("export_legal_articles_to_md")


@router.get("/export-md")
async def export_md_endpoint(
    input_dir: str,
    output_dir: str,
    max_tokens: int = 1000,
    overlap: int = 200,
    ext: str = ".md",
    title_template: str = "Article {label} (ID: {article_id})",
    body_heading: str = "TEXT",
) -> JSONResponse:
    """Export legal JSON articles to chunked Markdown files.

    Args:
        input_dir: Folder containing JSON or JSONL files.
        output_dir: Destination folder for Markdown files.
        max_tokens: Tokens per chunk (0 disables chunking).
        overlap: Token overlap between chunks.
        ext: Output file extension.
        title_template: Title format used in the Markdown output.
        body_heading: Heading shown before the article text.

    Returns:
        Summary of the export operation.
    """

    # Execute the export and capture resulting counts.
    art_count, file_count = _EXPORTER.export_folder(
        input_dir,
        output_dir,
        max_tokens=max_tokens,
        overlap_tokens=overlap,
        title_template=title_template,
        body_heading=body_heading,
        ext=ext,
    )

    # Report counts to the caller.
    return JSONResponse(
        {
            "articles": art_count,
            "files": file_count,
            "output_dir": output_dir,
        }
    )

"""Utility helpers for web routes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from fastapi.templating import Jinja2Templates  # type: ignore

from leropa.json_utils import json_loads

JSONDict = dict[str, Any]
DocumentSummary = dict[str, str | None]
DocumentSummaryList = list[DocumentSummary]

# Directory containing structured document files.
DOCUMENTS_DIR = Path(
    os.environ.get("LEROPA_DOCUMENTS", Path.home() / ".leropa" / "documents")
)

# Location of Jinja2 templates used by the web application.
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

# Jinja2 template renderer shared by route handlers.
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


def _document_files() -> list[Path]:
    """Return available document files from ``DOCUMENTS_DIR``.

    Returns:
        Paths pointing to JSON or YAML files. Nonexistent directories
        yield an empty list.
    """

    # Return early when directory does not exist.
    if not DOCUMENTS_DIR.exists():
        return []

    # Collect files with supported extensions.
    files: list[Path] = []
    for pattern in ("*.json", "*.yaml", "*.yml"):
        files.extend(DOCUMENTS_DIR.glob(pattern))
    return files


def _load_document_file(path: Path) -> JSONDict:
    """Load a structured document from ``path``.

    Args:
        path: Location of the JSON or YAML file.

    Returns:
        Parsed document dictionary.
    """

    text = path.read_text(encoding="utf-8")

    # Decode according to file extension.
    if path.suffix == ".json":
        return json_loads(text)  # type: ignore[return-value]
    return yaml.safe_load(text)


def _strip_full_text(doc: JSONDict) -> JSONDict:
    """Remove ``full_text`` from articles to expose granular content.

    Args:
        doc: Document structure to mutate.

    Returns:
        The same document with article ``full_text`` fields removed.
    """

    for article in doc.get("articles", []):
        article.pop("full_text", None)
    return doc

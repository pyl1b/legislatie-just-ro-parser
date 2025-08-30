"""Utility helpers for web routes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from leropa.json_utils import json_loads

JSONDict = dict[str, Any]
DocumentSummary = dict[str, str | None]
DocumentSummaryList = list[DocumentSummary]

# Directory containing structured document files.
DOCUMENTS_DIR = Path(
    os.environ.get("LEROPA_DOCUMENTS", Path.home() / ".leropa" / "documents")
)


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


def _render_document(doc: JSONDict) -> str:
    """Render a document structure into basic HTML.

    Args:
        doc: Parsed document data.

    Returns:
        HTML string representing the document.
    """

    parts = [f"<h1>{doc['document'].get('title', '')}</h1>"]

    # Render each article with its paragraphs and subparagraphs.
    for article in doc.get("articles", []):
        label = article.get("label", article.get("article_id", ""))
        parts.append(f"<h2>Art. {label}</h2>")

        for paragraph in article.get("paragraphs", []):
            par_label = paragraph.get("label", "")
            text = paragraph.get("text", "")
            parts.append(f"<p>{par_label} {text}</p>")

            # Include subparagraphs when present.
            for sub in paragraph.get("subparagraphs", []):
                sub_label = sub.get("label", "")
                sub_text = sub.get("text", "")
                parts.append(f"<p>{sub_label} {sub_text}</p>")
    return "".join(parts)

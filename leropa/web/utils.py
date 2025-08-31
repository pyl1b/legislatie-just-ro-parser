"""Utility helpers for web routes."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Literal

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


# Simple translation catalog for UI strings.
TRANSLATIONS: dict[str, dict[str, str]] = {
    "ro": {
        "rag_demo_title": "Demo RAG LeRoPa",
        "documents_link": "Documente",
        "ask_question_title": "Pune o întrebare",
        "your_question": "Întrebarea ta",
        "question_aria": "Întrebare",
        "ask_button": "Întreabă",
        "search_documents_title": "Caută documente",
        "search_query": "Căutare",
        "search_button": "Caută",
        "waiting_reply": "Se așteaptă răspuns...",
        "please_enter_question": "Te rog introdu o întrebare",
        "documents_title": "Documente",
        "administration_title": "Administrare",
        "document_id_placeholder": "ID document",
        "add_button": "Adaugă",
        "remove_selected": "Șterge selectate",
        "recreate_collection": "Recreează colecția",
        "processing": "Se procesează...",
        "collection_recreated": "Colecția a fost recreată",
        "source": "Sursa:",
        "document_not_found": "Document inexistent",
        "site_title": "LeRoPa",
    }
}


def get_translator(lang: str) -> Callable[[str, str], str]:
    """Return a translation function for ``lang``."""

    catalog = TRANSLATIONS.get(lang, {})

    def tr(code: str, default: str) -> str:
        """Translate ``code`` falling back to ``default``."""

        return catalog.get(code, default)

    return tr


def get_documents_dir() -> Path:
    """Return the current documents directory honoring environment changes.

    Returns:
        Path to the documents directory, using ``LEROPA_DOCUMENTS`` if set.
    """

    default_dir = Path.home() / ".leropa" / "documents"
    env_dir = os.environ.get("LEROPA_DOCUMENTS")
    return Path(env_dir) if env_dir else default_dir


def document_files() -> list[Path]:
    """Return available document files from ``DOCUMENTS_DIR``.

    Returns:
        Paths pointing to JSON or YAML files. Nonexistent directories
        yield an empty list.
    """

    # Compute the documents directory dynamically to honor environment changes.
    documents_dir = get_documents_dir()

    # Return early when directory does not exist.
    if not documents_dir.exists():
        return []

    # Collect files with supported extensions.
    files: list[Path] = []
    for pattern in ("*.json", "*.yaml", "*.yml"):
        files.extend(documents_dir.glob(pattern))
    return files


def load_document_file(path: Path) -> JSONDict:
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


def strip_full_text(doc: JSONDict) -> JSONDict:
    """Remove ``full_text`` from articles to expose granular content.

    Args:
        doc: Document structure to mutate.

    Returns:
        The same document with article ``full_text`` fields removed.
    """

    for article in doc.get("articles", []):
        article.pop("full_text", None)
    return doc


def create_jinja_context(
    lang: Literal["en", "ro"] = "en", **kwargs: object
) -> dict[str, object]:
    """Create additional variables for the Jinja2 template renderer.

    Args:
        lang: Language code used for translations.
        kwargs: Extra key-value pairs to inject into the template context.

    Returns:
        Mapping used as the Jinja2 context.
    """
    return {
        "is_str": lambda x: isinstance(x, str),
        "tr": get_translator(lang),
        "lang": lang,
        **kwargs,
    }

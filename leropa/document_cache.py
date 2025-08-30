"""Cache helpers for parsed documents."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml  # type: ignore[import-untyped]

from leropa.json_utils import json_loads
from leropa.parser.document_info import DocumentInfo

# Types for cache storage and JSON mappings.
JSONDict = Dict[str, Any]
CacheEntry = Tuple[float, DocumentInfo]
CacheStore = Dict[Path, CacheEntry]

# Global in-memory cache and its time-to-live in seconds.
_CACHE: CacheStore = {}
_TTL_SECONDS = 15 * 60


def load_document_info(path: Path) -> DocumentInfo:
    """Return document metadata for ``path`` using a timed cache.

    Args:
        path: Location of the JSON or YAML file containing the document.

    Returns:
        Parsed ``DocumentInfo`` describing the document.
    """
    now = time.time()
    cached = _CACHE.get(path)

    # Return cached entry when still valid.
    if cached and now - cached[0] < _TTL_SECONDS:
        return cached[1]

    # Load document structure and build ``DocumentInfo`` from the ``document``
    # section of the file.
    data = _load_document_file(path)
    info = DocumentInfo(**data["document"])

    # Store fresh entry in the cache.
    _CACHE[path] = (now, info)
    return info


def _load_document_file(path: Path) -> JSONDict:
    """Read a structured document file from ``path``.

    Args:
        path: Location of the JSON or YAML document file.

    Returns:
        Parsed document dictionary.
    """

    text = path.read_text(encoding="utf-8")

    # Decode JSON or YAML depending on file extension.
    if path.suffix == ".json":
        return json_loads(text)  # type: ignore[return-value]
    return yaml.safe_load(text)

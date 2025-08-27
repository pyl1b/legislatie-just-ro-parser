"""Fetch document HTML, using local cache when possible."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests  # type: ignore[import-untyped]

from .parse_html import parse_html

CACHE_DIR = Path.home() / ".leropa"


def fetch_document(
    ver_id: str, cache_dir: Path | None = None
) -> dict[str, Any]:
    """Fetch document HTML, using local cache when possible.

    Args:
        ver_id: Identifier for the document version to fetch.
        cache_dir: Directory used for caching downloaded HTML files.

    Returns:
        Parsed document structure.
    """

    cache_dir = cache_dir or CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{ver_id}.html"

    if cache_file.exists():
        html = cache_file.read_text(encoding="utf-8")
    else:
        url = f"https://legislatie.just.ro/Public/DetaliiDocument/{ver_id}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html = response.text
        cache_file.write_text(html, encoding="utf-8")

    return parse_html(html, ver_id)

"""Parse legal documents from legislatie.just.ro."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup, Tag

# Type aliases
ParagraphList = List[dict[str, str]]


@dataclass
class DocumentInfo:
    """Metadata about the parsed document.

    Attributes:
        source: Source URL for the document.
        ver_id: Identifier for the document version.
        prev_ver: Identifier for previous version if available.
        next_ver: Identifier for next version if available.
    """

    source: str
    ver_id: str
    prev_ver: str | None = None
    next_ver: str | None = None


@dataclass
class Article:
    """Represents a single article from the document.

    Attributes:
        article_id: Identifier for the article element in the source HTML.
        full_text: Full text content of the article.
        paragraphs: Ordered collection of paragraphs within the article.
    """

    article_id: str
    full_text: str
    paragraphs: ParagraphList = field(default_factory=list)


def _get_paragraphs(body_tag: Tag) -> ParagraphList:
    """Extract paragraph information from an article body tag."""

    paragraphs: ParagraphList = []

    for p_tag in body_tag.find_all("span", class_=["S_PAR", "S_ALN_BDY"]):
        # Paragraph identifier from the HTML element.
        par_id = p_tag.get("id", "")

        # Visible text without any markup.
        text = p_tag.get_text(strip=True)

        paragraphs.append({"par_id": par_id, "text": text})

    return paragraphs


def parse_html(html: str, ver_id: str) -> dict[str, object]:
    """Parse HTML content into structured data.

    Args:
        html: Raw HTML content of the legal document.
        ver_id: Identifier for the document version.

    Returns:
        Structured representation of the document.
    """

    soup = BeautifulSoup(html, "html.parser")

    articles: List[Article] = []

    for art_tag in soup.find_all("span", class_="S_ART"):
        # Unique identifier of the article.
        article_id = art_tag.get("id", "")

        body_tag = art_tag.find("span", class_="S_ART_BDY")
        if body_tag is None:
            # Skip if body is missing.
            continue

        paragraphs = _get_paragraphs(body_tag)

        # Full text of the article.
        full_text = body_tag.get_text(strip=True)

        articles.append(
            Article(
                article_id=article_id,
                full_text=full_text,
                paragraphs=paragraphs,
            )
        )

    source = f"https://legislatie.just.ro/Public/DetaliiDocument/{ver_id}"
    document = DocumentInfo(source=source, ver_id=ver_id)

    return {
        "document": document.__dict__,
        "articles": [a.__dict__ for a in articles],
    }


CACHE_DIR = Path.home() / ".leropa"


def fetch_document(
    ver_id: str, cache_dir: Path | None = None
) -> dict[str, object]:
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

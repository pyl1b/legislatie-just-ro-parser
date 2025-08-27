"""Parse legal documents from legislatie.just.ro."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup, Tag

# Type aliases
SubParagraphList = List["SubParagraph"]
ParagraphList = List["Paragraph"]


@dataclass
class SubParagraph:
    """Lettered sub-paragraph within a paragraph.

    Attributes:
        sub_id: Identifier for the sub-paragraph element in the source HTML.
        label: Enumerated label such as "a)".
        text: Visible text content of the sub-paragraph.
    """

    sub_id: str
    label: str
    text: str


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


@dataclass
class Paragraph:
    """Represents a paragraph from an article.

    Attributes:
        par_id: Identifier for the paragraph element in the source HTML.
        text: Visible text content of the paragraph.
        subparagraphs: Ordered collection of sub-paragraphs.
    """

    par_id: str
    text: str
    subparagraphs: SubParagraphList = field(default_factory=list)


def _get_paragraphs(body_tag: Tag) -> ParagraphList:
    """Extract paragraph information from an article body tag."""

    paragraphs: ParagraphList = []

    current_par: Paragraph | None = None

    for child in body_tag.find_all("span", recursive=False):
        classes = child.get("class", [])

        if "S_PAR" in classes or "S_ALN" in classes:
            # For numbered paragraphs wrapped in S_ALN, extract body text.
            if "S_ALN" in classes:
                bdy = child.find("span", class_="S_ALN_BDY")
                text = (
                    bdy.get_text(strip=True)
                    if bdy
                    else child.get_text(strip=True)
                )
            else:
                text = child.get_text(strip=True)

            par_id = child.get("id", "")
            current_par = Paragraph(par_id=par_id, text=text)
            paragraphs.append(current_par)
            continue

        if "S_LIT" in classes and current_par is not None:
            label_tag = child.find("span", class_="S_LIT_TTL")
            label = label_tag.get_text(strip=True) if label_tag else ""

            bdy = child.find("span", class_="S_LIT_BDY")
            text = (
                bdy.get_text(strip=True) if bdy else child.get_text(strip=True)
            )

            sub_id = child.get("id", "")
            current_par.subparagraphs.append(
                SubParagraph(sub_id=sub_id, label=label, text=text)
            )
            continue

        if "S_ALN_BDY" in classes:
            # Some documents may have S_ALN_BDY directly under the body.
            par_id = child.get("id", "")
            text = child.get_text(strip=True)
            current_par = Paragraph(par_id=par_id, text=text)
            paragraphs.append(current_par)

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
        "document": asdict(document),
        "articles": [asdict(a) for a in articles],
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

"""Parse HTML content into structured data."""

from __future__ import annotations

import re
from typing import Any

from attrs import asdict
from bs4 import BeautifulSoup

from .article import Article
from .book import Book
from .chapter import Chapter
from .document_info import DocumentInfo
from .history_entry import HistoryEntry
from .section import Section
from .subsection import Subsection
from .title import Title
from .types import ArticleDataList, HistoryList
from .utils import (
    _ensure_book,
    _ensure_chapter,
    _ensure_section,
    _ensure_subsection,
    _ensure_title,
    _parse_article,
)


def parse_html(html: str, ver_id: str) -> dict[str, Any]:
    """Parse HTML content into structured data.

    Args:
        html: Raw HTML content of the legal document.
        ver_id: Identifier for the document version.

    Returns:
        Structured representation of the document.
    """

    soup = BeautifulSoup(html, "html.parser")

    # Extract document metadata from meta tags.
    meta_title: Any = soup.find("meta", attrs={"name": "title"})
    description_tag: Any = soup.find("meta", attrs={"name": "description"})
    keywords_tag: Any = soup.find("meta", attrs={"name": "keywords"})

    # Fall back to the HTML title when meta title is missing.
    title = (
        meta_title.get("content")
        if meta_title and meta_title.get("content")
        else soup.title.get_text(strip=True)
        if soup.title
        else None
    )

    description = description_tag.get("content") if description_tag else None
    keywords = keywords_tag.get("content") if keywords_tag else None

    # Collect historical versions from the consolidation list.
    history: HistoryList = []
    history_div: Any = soup.find("div", id="istoric_fa")
    if history_div:
        # Iterate through all links representing previous versions.
        for link in history_div.find_all("a"):
            href = link.get("href")

            # Skip entries without hyperlinks as they point to the current
            # version.
            if not href:
                continue

            # Extract the version identifier from the URL.
            ver_match = re.search(r"/(\d+)(?:\?|$)", href)
            if not ver_match:
                continue

            # Determine the date from the link text or title attribute.
            text = link.get_text(strip=True)
            title_text = link.get("title", "")
            source = (
                text if re.search(r"\d{2}\.\d{2}\.\d{4}", text) else title_text
            )
            date_match = re.search(r"(\d{2}\.\d{2}\.\d{4})", source)
            if not date_match:
                continue

            history.append(
                HistoryEntry(
                    ver_id=ver_match.group(1), date=date_match.group(1)
                )
            )

    # Store all parsed articles for backward compatibility.
    parsed_articles: ArticleDataList = []

    # Temporary registries for hierarchical structures to avoid duplicates.
    books: dict[str, Book] = {}
    titles: dict[str, Title] = {}
    chapters: dict[str, Chapter] = {}
    sections: dict[str, Section] = {}
    subsections: dict[str, Subsection] = {}

    for art_tag in soup.find_all("span", class_="S_ART"):
        # Parse the article tag into a dataclass.
        article = _parse_article(art_tag)
        if article is None:
            continue

        # Ensure parent containers exist and retrieve them.
        book = _ensure_book(art_tag, books)
        title_obj = _ensure_title(art_tag, titles, book)
        chapter = _ensure_chapter(art_tag, chapters, title_obj, book)
        section = _ensure_section(art_tag, sections, chapter, title_obj, book)
        subsection = _ensure_subsection(art_tag, subsections, section)

        # Attach the article id to the deepest container available.
        if subsection:
            subsection.articles.append(article.article_id)
        elif section:
            section.articles.append(article.article_id)
        elif chapter:
            chapter.articles.append(article.article_id)
        elif title_obj:
            title_obj.articles.append(article.article_id)
        elif book:
            book.articles.append(article.article_id)

        parsed_articles.append(article)

    source = f"https://legislatie.just.ro/Public/DetaliiDocument/{ver_id}"

    # Store metadata and history in the document info.
    document = DocumentInfo(
        source=source,
        ver_id=ver_id,
        title=title,
        description=description,
        keywords=keywords,
        history=history,
        prev_ver=history[0].ver_id if history else None,
    )

    return {
        "document": asdict(document),
        "articles": [asdict(a) for a in parsed_articles],
        "books": [asdict(b) for b in books.values()],
    }

"""Parse legal documents from legislatie.just.ro."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, List

import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

# Type aliases
SubParagraphList = List["SubParagraph"]
ParagraphList = List["Paragraph"]
NoteList = List["Note"]
HistoryList = List["HistoryEntry"]
ArticleList = List[str]
ArticleDataList = List["Article"]
ChapterList = List["Chapter"]
TitleList = List["Title"]
BookList = List["Book"]
SectionList = List["Section"]
SubsectionList = List["Subsection"]


@dataclass
class SubParagraph:
    """Lettered or numbered sub-paragraph within a paragraph.

    Attributes:
        sub_id: Identifier for the sub-paragraph element in the source HTML.
        label: Enumerated label such as "a)" or "(1)".
        text: Visible text content of the sub-paragraph without the label.
    """

    sub_id: str
    label: str
    text: str


@dataclass
class HistoryEntry:
    """Version entry from the document history.

    Attributes:
        ver_id: Identifier for the document version.
        date: Consolidation or republication date.
    """

    ver_id: str
    date: str


@dataclass
class DocumentInfo:
    """Metadata about the parsed document.

    Attributes:
        source: Source URL for the document.
        ver_id: Identifier for the document version.
        title: Document title from the HTML metadata.
        description: Document description from the HTML metadata.
        keywords: Document keywords from the HTML metadata.
        history: Chronological list of earlier document versions.
        prev_ver: Identifier for previous version if available.
        next_ver: Identifier for next version if available.
    """

    source: str
    ver_id: str
    title: str | None = None
    description: str | None = None
    keywords: str | None = None
    history: HistoryList = field(default_factory=list)
    prev_ver: str | None = None
    next_ver: str | None = None


@dataclass
class Article:
    """Represents a single article from the document.

    Attributes:
        article_id: Identifier for the article element in the source HTML.
        full_text: Full text content of the article.
        paragraphs: Ordered collection of paragraphs within the article.
        notes: Notes attached to the article body.
    """

    article_id: str
    full_text: str
    paragraphs: ParagraphList = field(default_factory=list)
    notes: NoteList = field(default_factory=list)


@dataclass
class Paragraph:
    """Represents a paragraph from an article.

    Attributes:
        par_id: Identifier for the paragraph element in the source HTML.
        text: Visible text content of the paragraph without the label.
        label: Enumerated label such as "(1)" if present.
        subparagraphs: Ordered collection of sub-paragraphs.
        notes: Notes with amendment information.
    """

    par_id: str
    text: str
    label: str | None = None
    subparagraphs: SubParagraphList = field(default_factory=list)
    notes: NoteList = field(default_factory=list)


@dataclass
class Note:
    """Amendment note attached to an article or paragraph.

    Attributes:
        note_id: Identifier for the note element in the source HTML.
        text: Full textual content of the note.
        date: Date when the amendment took effect, if available.
        subject: Portion of the document that was modified.
        law_number: Number of the amending law.
        law_date: Publication date of the amending law.
        monitor_number: Number of the "Monitorul Oficial" issue.
        monitor_date: Date of the "Monitorul Oficial" issue.
        replaced: Text that was replaced.
        replacement: Text that replaced the original.
    """

    note_id: str
    text: str
    date: str | None = None
    subject: str | None = None
    law_number: str | None = None
    law_date: str | None = None
    monitor_number: str | None = None
    monitor_date: str | None = None
    replaced: str | None = None
    replacement: str | None = None


@dataclass
class Subsection:
    """Subsection grouping articles inside a section.

    Attributes:
        subsection_id: Identifier for the subsection body in the source HTML.
        title: Subsection label such as "§1".
        description: Descriptive text for the subsection if present.
        articles: Ordered list of article identifiers contained in the
            subsection.
    """

    subsection_id: str
    title: str
    description: str | None = None
    articles: ArticleList = field(default_factory=list)


@dataclass
class Section:
    """Section grouping subsections and articles.

    Attributes:
        section_id: Identifier for the section body in the source HTML.
        title: Section label such as "Secţiunea I".
        description: Descriptive text for the section if present.
        subsections: Ordered list of subsections within the section.
        articles: Identifiers of articles that appear directly under the
            section.
    """

    section_id: str
    title: str
    description: str | None = None
    subsections: SubsectionList = field(default_factory=list)
    articles: ArticleList = field(default_factory=list)


@dataclass
class Chapter:
    """Chapter grouping sections and articles.

    Attributes:
        chapter_id: Identifier for the chapter body in the source HTML.
        title: Chapter label such as "Capitolul I".
        description: Descriptive text for the chapter if present.
        sections: Ordered list of sections within the chapter.
        articles: Ordered list of article identifiers contained in the chapter.
    """

    chapter_id: str
    title: str
    description: str | None = None
    sections: SectionList = field(default_factory=list)
    articles: ArticleList = field(default_factory=list)


@dataclass
class Title:
    """Title grouping chapters, sections and articles.

    Attributes:
        title_id: Identifier for the title body in the source HTML.
        title: Title label such as "Titlul I".
        description: Descriptive text for the title if present.
        chapters: Ordered list of chapters within the title.
        sections: Ordered list of sections within the title.
        articles: Identifiers of articles that appear directly under the title.
    """

    title_id: str
    title: str
    description: str | None = None
    chapters: ChapterList = field(default_factory=list)
    sections: SectionList = field(default_factory=list)
    articles: ArticleList = field(default_factory=list)


@dataclass
class Book:
    """Book grouping titles, chapters, sections and articles.

    Attributes:
        book_id: Identifier for the book body in the source HTML.
        title: Book label such as "Cartea I".
        description: Descriptive text for the book if present.
        titles: Ordered list of titles within the book.
        chapters: Chapters directly contained in the book.
        sections: Sections directly contained in the book.
        articles: Identifiers of articles that appear directly under the book.
    """

    book_id: str
    title: str
    description: str | None = None
    titles: TitleList = field(default_factory=list)
    chapters: ChapterList = field(default_factory=list)
    sections: SectionList = field(default_factory=list)
    articles: ArticleList = field(default_factory=list)


def _normalize_whitespace(text: str) -> str:
    """Collapse consecutive whitespace and tidy punctuation spacing."""

    cleaned = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"\s+([,.;:!?\)])", r"\1", cleaned)


def _parse_note_details(text: str) -> dict[str, str | None]:
    """Extract structured information from an amendment note.

    Args:
        text: Note text with normalized whitespace.

    Returns:
        Dictionary with parsed fields, defaulting to ``None`` when data is
        missing.
    """

    date_match = re.search(r"la (\d{2}[.-]\d{2}[.-]\d{4})", text)
    date = date_match.group(1) if date_match else None

    subject = None
    if date_match:
        subject_match = re.search(r",\s*(.*?)\s+a fost", text)
        if subject_match:
            subject = subject_match.group(1)

    law_match = re.search(
        r"LEGEA nr\.\s*(\d+)\s+din\s+([0-9]{1,2} [a-zăâîșț]+ [0-9]{4})",
        text,
        re.IGNORECASE,
    )
    law_number = law_match.group(1) if law_match else None
    law_date = law_match.group(2) if law_match else None

    monitor_match = re.search(
        (
            r"MONITORUL OFICIAL nr\.\s*(\d+)\s+din\s+"
            r"([0-9]{1,2} [a-zăâîșț]+ [0-9]{4})"
        ),
        text,
        re.IGNORECASE,
    )
    monitor_number = monitor_match.group(1) if monitor_match else None
    monitor_date = monitor_match.group(2) if monitor_match else None

    replace_match = re.search(
        r'înlocuirea sintagmei "([^"]+)" cu sintagma "([^"]+)"',
        text,
        re.IGNORECASE,
    )
    replaced = replace_match.group(1) if replace_match else None
    replacement = replace_match.group(2) if replace_match else None

    return {
        "date": date,
        "subject": subject,
        "law_number": law_number,
        "law_date": law_date,
        "monitor_number": monitor_number,
        "monitor_date": monitor_date,
        "replaced": replaced,
        "replacement": replacement,
    }


def _note_from_tag(tag: Any) -> Note:  # noqa: ANN401
    """Create a Note instance from the given HTML tag."""

    note_id = str(tag.get("id", ""))
    text = _normalize_whitespace(tag.get_text(" ", strip=True))
    details = _parse_note_details(text)
    return Note(note_id=note_id, text=text, **details)


def _get_paragraphs(body_tag: Any) -> tuple[ParagraphList, NoteList]:  # noqa: ANN401
    """Extract paragraph and note information from an article body tag."""

    paragraphs: ParagraphList = []
    notes: NoteList = []

    current_par: Paragraph | None = None

    for child in body_tag.find_all("span", recursive=False):
        classes = child.get("class", [])

        # Handle article-level notes.
        if "S_NTA" in classes:
            title_tag = child.find("span", class_="S_NTA_TTL")
            if title_tag:
                title_tag.extract()

            notes.append(_note_from_tag(child))

            child.decompose()
            continue

        if "S_PAR" in classes or "S_ALN" in classes:
            # For numbered paragraphs wrapped in S_ALN,
            # extract body text and label.
            notes_in_par: NoteList = []
            if "S_ALN" in classes:
                bdy = child.find("span", class_="S_ALN_BDY")
                if bdy:
                    # Extract notes embedded within the paragraph body.
                    for note in bdy.find_all("span", class_="S_PAR"):
                        notes_in_par.append(_note_from_tag(note))
                        note.extract()

                # Preserve spaces between inline elements when extracting text.
                text = (
                    _normalize_whitespace(bdy.get_text(" ", strip=True))
                    if bdy
                    else _normalize_whitespace(child.get_text(" ", strip=True))
                )

                label_tag = child.find("span", class_="S_ALN_TTL")
                label = label_tag.get_text(strip=True) if label_tag else None
            else:
                # Extract notes embedded within plain paragraph tags.
                for note in child.find_all("span", class_="S_PAR"):
                    notes_in_par.append(_note_from_tag(note))
                    note.extract()

                # Preserve spaces between inline elements when extracting text.
                text = _normalize_whitespace(child.get_text(" ", strip=True))
                label = None

            par_id = child.get("id", "")
            current_par = Paragraph(
                par_id=par_id,
                text=text,
                label=label,
                notes=notes_in_par,
            )
            paragraphs.append(current_par)
            continue

        if "S_LIT" in classes:
            label_tag = child.find("span", class_="S_LIT_TTL")
            bdy = child.find("span", class_="S_LIT_BDY")

            notes_in_par = []
            if bdy:
                # Remove notes from the body and capture them when present.
                for note in bdy.find_all("span", class_="S_PAR"):
                    notes_in_par.append(_note_from_tag(note))
                    note.extract()

            # Preserve spaces between inline elements when extracting text.
            text = (
                _normalize_whitespace(bdy.get_text(" ", strip=True))
                if bdy
                else _normalize_whitespace(child.get_text(" ", strip=True))
            )

            label = label_tag.get_text(strip=True) if label_tag else ""
            if not label:
                # Extract label from the body when missing from S_LIT_TTL.
                match = re.match(r"^(\([0-9]+\)|[a-z]\))", text)
                if match:
                    label = match.group(1)
                    text = text[match.end() :].lstrip()

            # Determine whether this is a paragraph or subparagraph.
            if re.match(r"^\([0-9]+\)$", label) and (
                current_par is None or current_par.label is not None
            ):
                par_id = child.get("id", "")
                current_par = Paragraph(
                    par_id=par_id,
                    text=text,
                    label=label,
                    notes=notes_in_par,
                )
                paragraphs.append(current_par)
            elif current_par is not None:
                sub_id = child.get("id", "")
                current_par.subparagraphs.append(
                    SubParagraph(sub_id=sub_id, label=label, text=text)
                )
            else:
                # Treat stray S_LIT elements as paragraphs without labels.
                par_id = child.get("id", "")
                current_par = Paragraph(
                    par_id=par_id,
                    text=text,
                    label=None,
                    notes=notes_in_par,
                )
                paragraphs.append(current_par)
            continue

        if "S_ALN_BDY" in classes:
            # Some documents may have S_ALN_BDY directly under the body.
            for note in child.find_all("span", class_="S_PAR"):
                note.extract()
            par_id = child.get("id", "")

            # Preserve spaces between inline elements when extracting text.
            text = _normalize_whitespace(child.get_text(" ", strip=True))
            match = re.match(r"^(\([0-9]+\))", text)
            label = match.group(1) if match else None
            if match:
                text = text[match.end() :].lstrip()
            current_par = Paragraph(par_id=par_id, text=text, label=label)
            paragraphs.append(current_par)

    return paragraphs, notes


def _parse_article(art_tag: Any) -> Article | None:  # noqa: ANN401
    """Create an article dataclass from the given tag.

    Args:
        art_tag: Tag representing the article in the HTML.

    Returns:
        Parsed Article instance or ``None`` when body is missing.
    """

    # Unique identifier of the article.
    article_id = art_tag.get("id", "")

    # Body container that holds the paragraphs and notes.
    body_tag = art_tag.find("span", class_="S_ART_BDY")
    if body_tag is None:
        return None

    # Remove hidden short placeholders that render as ellipsis.
    # These spans contain only three dots ("...") and are not meant to be
    # part of the visible text content.
    for short in body_tag.find_all("span", class_="S_LIT_SHORT"):
        short.decompose()

    # Extract paragraphs and associated notes.
    paragraphs, notes = _get_paragraphs(body_tag)

    # Full text of the article without notes.

    # Preserve spaces between inline elements when extracting text.
    full_text = _normalize_whitespace(body_tag.get_text(" ", strip=True))

    return Article(
        article_id=article_id,
        full_text=full_text,
        paragraphs=paragraphs,
        notes=notes,
    )


def _ensure_book(art_tag: Any, books: dict[str, Book]) -> Book | None:  # noqa: ANN401
    """Retrieve or create a book for the given article tag."""

    # Locate the nearest book body containing the article.
    book_body = art_tag.find_parent("span", class_="S_CRT_BDY")
    if not book_body:
        return None

    # Use the book body identifier to deduplicate books.
    book_id = book_body.get("id", "")
    if book_id in books:
        return books[book_id]

    # Determine the book title and description from preceding siblings.
    title_tag = book_body.find_previous("span", class_="S_CRT_TTL")
    desc_tag = book_body.find_previous("span", class_="S_CRT_DEN")

    # Textual information for the book.
    title = title_tag.get_text(strip=True) if title_tag else ""
    description = desc_tag.get_text(strip=True) if desc_tag else None

    # Create and store the new book instance.
    book = Book(book_id=book_id, title=title, description=description)
    books[book_id] = book
    return book


def _ensure_title(
    art_tag: Any,  # noqa: ANN401
    titles: dict[str, Title],
    book: Book | None,
) -> Title | None:
    """Retrieve or create a title for the given article tag."""

    # Locate the nearest title body containing the article.
    title_body = art_tag.find_parent("span", class_="S_TTL_BDY")
    if not title_body:
        return None

    # Use the title body identifier to deduplicate titles.
    title_id = title_body.get("id", "")
    title_obj = titles.get(title_id)

    if title_obj is None:
        # Determine the title label and description from preceding siblings.
        title_tag = title_body.find_previous("span", class_="S_TTL_TTL")
        desc_tag = title_body.find_previous("span", class_="S_TTL_DEN")

        # Textual information for the title.
        title_text = title_tag.get_text(strip=True) if title_tag else ""
        description = desc_tag.get_text(strip=True) if desc_tag else None

        # Create and store the new title instance.
        title_obj = Title(
            title_id=title_id,
            title=title_text,
            description=description,
        )
        titles[title_id] = title_obj

    # Attach the title to the parent book if needed.
    if book and all(t.title_id != title_id for t in book.titles):
        book.titles.append(title_obj)

    return title_obj


def _ensure_chapter(
    art_tag: Any,  # noqa: ANN401
    chapters: dict[str, Chapter],
    title: Title | None,
    book: Book | None,
) -> Chapter | None:
    """Retrieve or create a chapter for the given article tag."""

    # Locate the nearest chapter body containing the article.
    chapter_body = art_tag.find_parent("span", class_="S_CAP_BDY")
    if not chapter_body:
        return None

    # Use the chapter body identifier to deduplicate chapters.
    chapter_id = chapter_body.get("id", "")
    chapter = chapters.get(chapter_id)

    if chapter is None:
        # Determine the chapter label and description from preceding siblings.
        title_tag = chapter_body.find_previous("span", class_="S_CAP_TTL")
        desc_tag = chapter_body.find_previous("span", class_="S_CAP_DEN")

        # Textual information for the chapter.
        chap_title = title_tag.get_text(strip=True) if title_tag else ""
        description = desc_tag.get_text(strip=True) if desc_tag else None

        # Create and store the new chapter instance.
        chapter = Chapter(
            chapter_id=chapter_id,
            title=chap_title,
            description=description,
        )
        chapters[chapter_id] = chapter

    # Attach the chapter to the parent title or book.
    if title and all(c.chapter_id != chapter_id for c in title.chapters):
        title.chapters.append(chapter)
    elif book and all(c.chapter_id != chapter_id for c in book.chapters):
        book.chapters.append(chapter)

    return chapter


def _ensure_section(
    art_tag: Any,  # noqa: ANN401
    sections: dict[str, Section],
    chapter: Chapter | None,
    title: Title | None,
    book: Book | None,
) -> Section | None:
    """Retrieve or create a section for the given article tag."""

    # Locate the nearest section body containing the article.
    section_body = art_tag.find_parent("span", class_="S_SEC_BDY")
    if not section_body:
        return None

    # Use the section body identifier to deduplicate sections.
    section_id = section_body.get("id", "")
    section = sections.get(section_id)

    if section is None:
        # Determine the section label and description from preceding siblings.
        title_tag = section_body.find_previous("span", class_="S_SEC_TTL")
        desc_tag = section_body.find_previous("span", class_="S_SEC_DEN")

        # Textual information for the section.
        sec_title = title_tag.get_text(strip=True) if title_tag else ""
        description = desc_tag.get_text(strip=True) if desc_tag else None

        # Create and store the new section instance.
        section = Section(
            section_id=section_id,
            title=sec_title,
            description=description,
        )
        sections[section_id] = section

    # Attach the section to the parent container.
    if chapter and all(s.section_id != section_id for s in chapter.sections):
        chapter.sections.append(section)
    elif (
        title
        and hasattr(title, "sections")
        and all(s.section_id != section_id for s in title.sections)
    ):
        title.sections.append(section)
    elif (
        book
        and hasattr(book, "sections")
        and all(s.section_id != section_id for s in book.sections)
    ):
        book.sections.append(section)

    return section


def _ensure_subsection(
    art_tag: Any,  # noqa: ANN401
    subsections: dict[str, Subsection],
    section: Section | None,
) -> Subsection | None:
    """Retrieve or create a subsection for the given article tag."""

    if not section:
        return None

    # Locate the nearest subsection body containing the article.
    sub_body = art_tag.find_parent("span", class_="S_SSEC_BDY")
    if not sub_body:
        return None

    # Use the subsection body identifier to deduplicate subsections.
    sub_id = sub_body.get("id", "")
    subsection = subsections.get(sub_id)

    if subsection is None:
        # Determine the subsection label and description.
        # Use preceding siblings to extract metadata.
        title_tag = sub_body.find_previous("span", class_="S_SSEC_TTL")
        desc_tag = sub_body.find_previous("span", class_="S_SSEC_DEN")

        # Textual information for the subsection.
        sub_title = title_tag.get_text(strip=True) if title_tag else ""
        description = desc_tag.get_text(strip=True) if desc_tag else None

        # Create and store the new subsection instance.
        subsection = Subsection(
            subsection_id=sub_id,
            title=sub_title,
            description=description,
        )
        subsections[sub_id] = subsection

    # Attach the subsection to the parent section.
    if all(s.subsection_id != sub_id for s in section.subsections):
        section.subsections.append(subsection)

    return subsection


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
        # Include the parsed history.
        history=history,
        # The latest previous version becomes prev_ver for convenience.
        prev_ver=history[0].ver_id if history else None,
    )

    return {
        "document": asdict(document),
        "articles": [asdict(a) for a in parsed_articles],
        "books": [asdict(b) for b in books.values()],
    }


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

"""Utility functions for parsing document structures."""

from __future__ import annotations

import re
from typing import Any

from .article import Article
from .book import Book
from .chapter import Chapter
from .note import Note
from .paragraph import Paragraph
from .section import Section
from .sub_paragraph import SubParagraph
from .subsection import Subsection
from .title import Title
from .types import NoteList, ParagraphList


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

            # Collect line items before extracting paragraph text so that
            # they don't end up in the paragraph body.
            line_items = child.find_all("span", class_="S_LIN")
            for item in line_items:
                item.extract()

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

            # Convert each extracted line item into a subparagraph of the
            # current paragraph.
            for item in line_items:
                label_tag = item.find("span", class_="S_LIN_TTL")
                bdy = item.find("span", class_="S_LIN_BDY")

                # Preserve spaces between inline elements when extracting text.
                sub_text = (
                    _normalize_whitespace(bdy.get_text(" ", strip=True))
                    if bdy
                    else _normalize_whitespace(item.get_text(" ", strip=True))
                )

                sub_label = label_tag.get_text(strip=True) if label_tag else ""
                sub_id = item.get("id", "")
                current_par.subparagraphs.append(
                    SubParagraph(sub_id=sub_id, label=sub_label, text=sub_text)
                )

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
    for short in body_tag.find_all(
        "span", class_=["S_LIT_SHORT", "S_LIN_SHORT"]
    ):
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

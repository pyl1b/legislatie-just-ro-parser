"""Represents a single article from the document."""

from __future__ import annotations

from attrs import define, field

from .types import NoteList, ParagraphList


@define(slots=True)
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
    paragraphs: ParagraphList = field(factory=list, repr=False)
    notes: NoteList = field(factory=list, repr=False)

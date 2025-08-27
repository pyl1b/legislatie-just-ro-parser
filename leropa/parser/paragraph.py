"""Represents a paragraph from an article."""

from __future__ import annotations

from attrs import define, field

from .types import NoteList, SubParagraphList


@define(slots=True)
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
    subparagraphs: SubParagraphList = field(factory=list, repr=False)
    notes: NoteList = field(factory=list, repr=False)

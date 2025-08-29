"""Data model for document annexes."""

from __future__ import annotations

from attrs import define, field

from .types import NoteList


@define(slots=True)
class Annex:
    """Represents an annex attached to the legal document.

    Attributes:
        annex_id: Identifier for the annex element in the source HTML.
        title: Title of the annex.
        text: Full textual content of the annex.
        notes: Notes or changes applied to the annex.
    """

    annex_id: str
    title: str
    text: str
    notes: NoteList = field(factory=list, repr=False)

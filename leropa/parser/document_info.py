"""Metadata about the parsed document."""

from __future__ import annotations

from attrs import define, field

from .history_entry import HistoryEntry
from .types import HistoryList


@define(slots=True)
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
    history: HistoryList = field(factory=list, repr=False)
    prev_ver: str | None = None
    next_ver: str | None = None

"""Version entry from the document history."""

from __future__ import annotations

from attrs import define


@define(slots=True)
class HistoryEntry:
    """Version entry from the document history.

    Attributes:
        ver_id: Identifier for the document version.
        date: Consolidation or republication date.
    """

    ver_id: str
    date: str

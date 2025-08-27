"""Amendment note attached to an article or paragraph."""

from __future__ import annotations

from attrs import define


@define(slots=True)
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

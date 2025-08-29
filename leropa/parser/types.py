"""Common type aliases for parser structures."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .annex import Annex  # noqa: F401
    from .article import Article  # noqa: F401
    from .book import Book  # noqa: F401
    from .chapter import Chapter  # noqa: F401
    from .history_entry import HistoryEntry  # noqa: F401
    from .note import Note  # noqa: F401
    from .paragraph import Paragraph  # noqa: F401
    from .section import Section  # noqa: F401
    from .sub_paragraph import SubParagraph  # noqa: F401
    from .title import Title  # noqa: F401


SubParagraphList = list["SubParagraph"]
ParagraphList = list["Paragraph"]
NoteList = list["Note"]
HistoryList = list["HistoryEntry"]
ArticleList = list[str]
ArticleDataList = list["Article"]
ChapterList = list["Chapter"]
TitleList = list["Title"]
BookList = list["Book"]
SectionList = list["Section"]
AnnexList = list["Annex"]

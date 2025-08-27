"""Book grouping titles, chapters, sections and articles."""

from __future__ import annotations

from attrs import define, field

from .types import ArticleList, ChapterList, SectionList, TitleList


@define(slots=True)
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
    titles: TitleList = field(factory=list, repr=False)
    chapters: ChapterList = field(factory=list, repr=False)
    sections: SectionList = field(factory=list, repr=False)
    articles: ArticleList = field(factory=list, repr=False)

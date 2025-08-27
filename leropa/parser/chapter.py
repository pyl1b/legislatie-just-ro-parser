"""Chapter grouping sections and articles."""

from __future__ import annotations

from attrs import define, field

from .types import ArticleList, SectionList


@define(slots=True)
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
    sections: SectionList = field(factory=list, repr=False)
    articles: ArticleList = field(factory=list, repr=False)

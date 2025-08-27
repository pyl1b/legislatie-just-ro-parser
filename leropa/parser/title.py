"""Title grouping chapters, sections and articles."""

from __future__ import annotations

from attrs import define, field

from .types import ArticleList, ChapterList, SectionList


@define(slots=True)
class Title:
    """Title grouping chapters, sections and articles.

    Attributes:
        title_id: Identifier for the title body in the source HTML.
        title: Title label such as "Titlul I".
        description: Descriptive text for the title if present.
        chapters: Ordered list of chapters within the title.
        sections: Ordered list of sections within the title.
        articles: Identifiers of articles that appear directly under the title.
    """

    title_id: str
    title: str
    description: str | None = None
    chapters: ChapterList = field(factory=list, repr=False)
    sections: SectionList = field(factory=list, repr=False)
    articles: ArticleList = field(factory=list, repr=False)

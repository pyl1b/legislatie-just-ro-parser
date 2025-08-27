"""Section grouping subsections and articles."""

from __future__ import annotations

from attrs import define, field

from .types import ArticleList, SectionList


@define(slots=True)
class Section:
    """Section grouping subsections and articles.

    Attributes:
        section_id: Identifier for the section body in the source HTML.
        title: Section label such as "Secţiunea I".
        description: Descriptive text for the section if present.
        level: Depth level derived from the section numeric title.
        subsections: Ordered list of nested sections.
        articles: Identifiers of articles that appear directly under the
            section.
    """

    section_id: str
    title: str
    description: str | None = None
    level: int = 1
    subsections: SectionList = field(factory=list, repr=False)
    articles: ArticleList = field(factory=list, repr=False)

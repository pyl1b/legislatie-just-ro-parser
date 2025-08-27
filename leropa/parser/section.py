"""Section grouping subsections and articles."""

from __future__ import annotations

from attrs import define, field

from .types import ArticleList, SubsectionList


@define(slots=True)
class Section:
    """Section grouping subsections and articles.

    Attributes:
        section_id: Identifier for the section body in the source HTML.
        title: Section label such as "Secţiunea I".
        description: Descriptive text for the section if present.
        subsections: Ordered list of subsections within the section.
        articles: Identifiers of articles that appear directly under the
            section.
    """

    section_id: str
    title: str
    description: str | None = None
    subsections: SubsectionList = field(factory=list, repr=False)
    articles: ArticleList = field(factory=list, repr=False)

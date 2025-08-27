"""Subsection grouping articles inside a section."""

from __future__ import annotations

from attrs import define, field

from .types import ArticleList


@define(slots=True)
class Subsection:
    """Subsection grouping articles inside a section.

    Attributes:
        subsection_id: Identifier for the subsection body in the source HTML.
        title: Subsection label such as "§1".
        description: Descriptive text for the subsection if present.
        articles: Ordered list of article identifiers contained in the
            subsection.
    """

    subsection_id: str
    title: str
    description: str | None = None
    articles: ArticleList = field(factory=list, repr=False)

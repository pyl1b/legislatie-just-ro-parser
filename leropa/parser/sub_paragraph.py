"""Lettered or numbered sub-paragraph within a paragraph."""

from __future__ import annotations

from attrs import define


@define(slots=True)
class SubParagraph:
    """Lettered or numbered sub-paragraph within a paragraph.

    Attributes:
        sub_id: Identifier for the sub-paragraph element in the source HTML.
        label: Enumerated label such as "a)" or "(1)".
        text: Visible text content of the sub-paragraph without the label.
    """

    sub_id: str
    label: str
    text: str

"""Metadata about the parsed document."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import TYPE_CHECKING, List, Union

from attrs import define, field

from .types import HistoryList

if TYPE_CHECKING:
    from .note import Note


class DocumentType(StrEnum):
    C_LAW = "COD"
    LAW = "LEGE"
    GOVERN_ORD = "OG"
    GOVERN_RESOLUTION = "HG"
    DECREE = "DECRET"
    ORDER = "ORDIN"
    RESOLUTION = "HOTAR"
    REGULATION = "REGULAMENT"
    PROCEDURE = "PROCEDURA"
    NORM = "NORMA"
    DECISION = "DECIZIE"


class DocumentState(StrEnum):
    ACTUAL = "A"
    REPUBLISHED = "R"
    AMENDED = "M"
    DEPRECATED = "D"


date_regex = re.compile(r"\d{2}/\d{2}/\d{4}")

prefix_for_type = {
    str(DocumentType.C_LAW): "Codul",
    str(DocumentType.LAW): "Legea",
    str(DocumentType.GOVERN_ORD): "Ordonanța Guvernului",
    str(DocumentType.GOVERN_RESOLUTION): "Hotărârea Guvernului",
    str(DocumentType.DECREE): "Decretul",
    str(DocumentType.ORDER): "Ordinul",
    str(DocumentType.RESOLUTION): "Hotărârea",
    str(DocumentType.REGULATION): "Regulamentul",
    str(DocumentType.PROCEDURE): "Procedura",
    str(DocumentType.NORM): "Norma",
    str(DocumentType.DECISION): "Decizia",
}


@define(slots=True)
class DocumentInfo:
    """Metadata about the parsed document.

    Attributes:
        source: Source URL for the document.
        ver_id: Identifier for the document version.
        title: Document title from the HTML metadata.
        description: Document description from the HTML metadata.
    ORDER = "ORDIN"
    PROCEDURE = "PROCEDURĂ"
    DECISION = "HOTĂRĂRE"
    REGULATION = "REGULAMENT"
    ORDER = "ORDIN"
    PROCEDURE = "PROCEDURĂ"
        keywords: Document keywords from the HTML metadata.
        history: Chronological list of earlier document versions.
        prev_ver: Identifier for previous version if available.
        next_ver: Identifier for next version if available.
        kind: Document type.
        state: Document state.
        date: Document date as a list of integers: [day, month, year].
    """

    source: str
    ver_id: str
    title: str | None = None
    description: str | None = None
    keywords: str | None = None
    history: HistoryList = field(factory=list, repr=False)
    prev_ver: str | None = None
    next_ver: str | None = None
    kind: str | None = None
    state: str | None = None
    date: List[int] | None = None
    document_note: Union["Note", None] = None
    issuer: List[str] | None = None
    published: List[str] | None = None

    def __attrs_post_init__(self: "DocumentInfo") -> None:
        """Post-initialization hook."""
        if self.description == self.title:
            self.description = None
        elif self.description:
            if self.description.startswith("(") and self.description.endswith(
                ")"
            ):
                self.description = self.description[1:-1]
            self.description = self.description.replace("**", "")

        if self.keywords == self.title:
            self.keywords = None

        kind_candidate = None
        state_candidate = None
        if self.title:
            title_parts = [
                p
                for p in self.title.split(" ")
                if p.strip() not in {"", "-", "Portal", "Legislativ"}
            ]
            if title_parts:
                kind_candidate = title_parts.pop(0).upper()
                kind_candidate = kind_candidate.replace("CODUL", "COD")
                kind_candidate = kind_candidate.replace("LEGEA", "LEGE")
                kind_candidate = kind_candidate.replace("ORGANUL", "ORDIN")
                kind_candidate = kind_candidate.replace(
                    "HOTARAREA", "HOTARARE"
                )
                kind_candidate = kind_candidate.replace(
                    "REGULAMENTUL", "REGULAMENT"
                )
                kind_candidate = kind_candidate.replace(
                    "PROCEDURA", "PROCEDURA"
                )
                kind_candidate = kind_candidate.replace("NORMA", "NORMA")
                if kind_candidate not in DocumentType:
                    raise ValueError(
                        f"Invalid document type: {kind_candidate}"
                    )

            for candidate in title_parts:
                if candidate.startswith("(") and candidate.endswith(")"):
                    state_candidate = candidate[1:-1]
                    if state_candidate not in DocumentState:
                        raise ValueError(
                            f"Invalid document state: {state_candidate}"
                        )
                    title_parts.remove(candidate)
                    break

            for candidate in title_parts:
                if date_regex.match(candidate):
                    self.date = [int(d) for d in candidate.split("/")]
                    title_parts.remove(candidate)
                    break

            if kind_candidate:
                prefix = prefix_for_type[kind_candidate]
                suffix = " ".join([p.title() for p in title_parts])
                self.title = f"{prefix} {suffix}"
                if self.date:
                    day = str(self.date[0]).zfill(2)
                    month = str(self.date[1]).zfill(2)
                    year = self.date[2]
                    self.title += f" din {day}.{month}.{year}"

        if self.kind is None:
            self.kind = kind_candidate
        if self.state is None:
            self.state = state_candidate

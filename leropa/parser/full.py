from typing import TYPE_CHECKING, Any

from attrs import define, field

if TYPE_CHECKING:
    from .annex import Annex
    from .article import Article
    from .book import Book
    from .document_info import DocumentInfo


@define(slots=True)
class FullDocumentVersion:
    """Represents a full document version.

    Attributes:
        document: Document information.
        articles: List of articles.
        books: List of books.
        annexes: List of annexes.
    """

    document: "DocumentInfo"
    articles: list["Article"] = field(factory=list)
    books: list["Book"] = field(factory=list)
    annexes: list["Annex"] = field(factory=list)

    @classmethod
    def from_raw_data(cls, raw_data: dict[str, Any]) -> "FullDocumentVersion":
        """Create a full document version from raw data.

        Args:
            raw_data: Raw data to create the full document version from.

        Returns:
            The full content of the document at a given version.
        """
        from .annex import Annex
        from .article import Article
        from .book import Book
        from .document_info import DocumentInfo

        document = DocumentInfo(**raw_data["document"])
        articles = [Article(**a) for a in raw_data.get("articles", [])]
        books = [Book(**b) for b in raw_data.get("books", [])]
        annexes = [Annex(**a) for a in raw_data.get("annexes", [])]

        return cls(
            document=document,
            articles=articles,
            books=books,
            annexes=annexes,
        )

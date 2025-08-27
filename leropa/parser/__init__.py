"""Parser package for legal documents."""

from .fetch_document import fetch_document
from .parse_html import parse_html

__all__ = ["fetch_document", "parse_html"]

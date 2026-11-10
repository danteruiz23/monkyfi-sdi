"""Ingestion (RF01): read the documents of an order package, keeping page and location.

Document text is untrusted data. Nothing here interprets it as instructions.
"""

from .documents import Document, Page, read_document, read_package

__all__ = ["Document", "Page", "read_document", "read_package"]

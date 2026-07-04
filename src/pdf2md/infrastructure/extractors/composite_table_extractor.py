"""Composite table extractor with primary and fallback engines."""

from __future__ import annotations

from pathlib import Path

from pdf2md.domain.entities.entities import TableNode
from pdf2md.domain.ports.ports import ITableExtractor


class CompositeTableExtractor(ITableExtractor):
    """Try a primary extractor, then optional fallbacks."""

    def __init__(
        self,
        primary: ITableExtractor,
        *fallbacks: ITableExtractor,
    ) -> None:
        self._extractors = (primary, *fallbacks)

    def extract_tables(
        self, pdf_path: Path, page_number: int
    ) -> list[TableNode]:
        for index, extractor in enumerate(self._extractors):
            tables = extractor.extract_tables(pdf_path, page_number)
            if tables:
                return tables
            if index == 0 and tables is not None:
                continue
        return []


class DocumentScopedTableExtractor(ITableExtractor):
    """Delegate to an inner extractor while keeping a document-level scope."""

    def __init__(self, inner: ITableExtractor) -> None:
        self._inner = inner
        self._pdf_path: Path | None = None

    def begin_document(self, pdf_path: Path) -> None:
        """Notify the inner extractor that a document extraction started."""
        self._pdf_path = pdf_path
        begin = getattr(self._inner, "begin_document", None)
        if callable(begin):
            begin(pdf_path)

    def end_document(self) -> None:
        """Release any document-level resources."""
        end = getattr(self._inner, "end_document", None)
        if callable(end):
            end()
        self._pdf_path = None

    def extract_tables(
        self, pdf_path: Path, page_number: int
    ) -> list[TableNode]:
        path = self._pdf_path or pdf_path
        return self._inner.extract_tables(path, page_number)


__all__ = ["CompositeTableExtractor", "DocumentScopedTableExtractor"]

"""Tests for the abstract ports.

We instantiate each port through a tiny in-memory implementation to
verify the contracts are usable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pdf2md.domain.entities.entities import (
    MarkdownDocument,
    PdfDocument,
)
from pdf2md.domain.ports.ports import (
    IBatchRunner,
    IExtractor,
    IImageExtractor,
    ILinkExtractor,
    IRenderer,
    IStorage,
    ITableExtractor,
)


class _Extractor(IExtractor):
    def extract(self, pdf_path: Path) -> PdfDocument:
        return PdfDocument(file_path=pdf_path, page_count=0)


class _Renderer(IRenderer):
    def render(self, document: PdfDocument) -> MarkdownDocument:
        return MarkdownDocument(source_pdf=document.file_path)


class _Storage(IStorage):
    def save(self, document: MarkdownDocument, source: PdfDocument | None = None) -> Path:
        return Path("memory://test.md")


class _ImageExtractor(IImageExtractor):
    def extract_images(self, page):  # type: ignore[override]
        return []


class _TableExtractor(ITableExtractor):
    def extract_tables(self, pdf_path: Path, page_number: int):
        return []


class _LinkExtractor(ILinkExtractor):
    def extract_links(self, pdf_path: Path):
        return []


class _Runner(IBatchRunner):
    def run(self, items, worker, *, workers):
        return [worker(i) for i in items]


class TestPortsAreUsable:
    """Each port should be instantiable through a concrete subclass."""

    def test_extractor(self) -> None:
        extractor = _Extractor()
        assert extractor.extract(Path("x.pdf")).page_count == 0

    def test_renderer(self) -> None:
        renderer = _Renderer()
        out = renderer.render(PdfDocument(file_path=Path("x.pdf"), page_count=0))
        assert isinstance(out, MarkdownDocument)

    def test_storage_with_source(self) -> None:
        storage = _Storage()
        out = storage.save(MarkdownDocument(source_pdf=Path("x.pdf")))
        assert out == Path("memory://test.md")

    def test_storage_without_source(self) -> None:
        storage = _Storage()
        out = storage.save(MarkdownDocument(source_pdf=Path("x.pdf")), source=None)
        assert out == Path("memory://test.md")

    def test_image_extractor(self) -> None:
        assert _ImageExtractor().extract_images(None) == []  # type: ignore[arg-type]

    def test_table_extractor(self) -> None:
        assert _TableExtractor().extract_tables(Path("x.pdf"), 1) == []

    def test_link_extractor(self) -> None:
        assert _LinkExtractor().extract_links(Path("x.pdf")) == []

    def test_batch_runner(self) -> None:
        runner = _Runner()
        result = runner.run([1, 2, 3], lambda x: x * 2, workers=2)
        assert result == [2, 4, 6]

    def test_cannot_instantiate_abstract(self) -> None:
        """The ABCs cannot be instantiated directly."""
        for cls in (IExtractor, IRenderer, IStorage, IBatchRunner):
            with pytest.raises(TypeError):
                cls()  # type: ignore[abstract]

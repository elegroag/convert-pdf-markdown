"""Integration tests for pdf2md improvements."""

from __future__ import annotations

import pytest

from pdf2md.domain.exceptions import EncryptedPdfError
from pdf2md.domain.value_objects.enums import TableEngine
from pdf2md.domain.value_objects.value_objects import ConversionConfig
from pdf2md.infrastructure.extractors.pymupdf_extractor import PyMuPdfExtractor
from pdf2md.infrastructure.extractors.table_extractor_factory import (
    build_default_table_extractor,
)


class TestEncryptedPdfPipeline:
    def test_extract_with_password_via_config(
        self, pdf_path: callable
    ) -> None:
        path = pdf_path("encrypted.pdf")
        extractor = PyMuPdfExtractor(
            config=ConversionConfig(password="secret"),
            table_extractor=build_default_table_extractor(TableEngine.PDFPLUMBER),
        )
        doc = extractor.extract(path)
        assert doc.page_count == 1
        assert "Secret Document" in doc.pages[0].raw_text

    def test_extract_without_password_raises(
        self, pdf_path: callable
    ) -> None:
        path = pdf_path("encrypted.pdf")
        with pytest.raises(EncryptedPdfError):
            PyMuPdfExtractor().extract(path)


class TestPagesFilter:
    def test_pages_filter_limits_extracted_pages(
        self, pdf_path: callable
    ) -> None:
        path = pdf_path("simple.pdf")
        extractor = PyMuPdfExtractor(
            config=ConversionConfig(pages_filter="1"),
            table_extractor=build_default_table_extractor(TableEngine.PDFPLUMBER),
        )
        doc = extractor.extract(path)
        assert doc.page_count == 1
        assert doc.pages[0].page_number == 1


class TestMulticolumnMarkdown:
    def test_multicolumn_markdown_preserves_reading_order(
        self, pdf_path: callable, renderer
    ) -> None:
        path = pdf_path("multicolumn.pdf")
        extractor = PyMuPdfExtractor(
            config=ConversionConfig(image_min_size=50),
            table_extractor=build_default_table_extractor(TableEngine.PDFPLUMBER),
        )
        doc = extractor.extract(path)
        md = renderer.render(doc).to_string()
        assert "Lorem" in md
        assert len(doc.pages[0].blocks) >= 3

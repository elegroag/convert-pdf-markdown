"""Tests for the PyMuPdfExtractor adapter using a fake ``fitz`` module.

These tests cover the orchestration code in :class:`PyMuPdfExtractor`
without requiring real PDFs. The lower-level fitz interactions are
verified separately by integration tests against real fixtures.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pdf2md.domain.exceptions import (
    CorruptedPdfError,
    EncryptedPdfError,
)
from pdf2md.domain.value_objects.enums import TableEngine
from pdf2md.domain.value_objects.value_objects import ConversionConfig
from pdf2md.infrastructure.extractors.pymupdf_extractor import PyMuPdfExtractor
from pdf2md.infrastructure.extractors.table_extractor_factory import (
    build_default_table_extractor,
)


def _make_fake_page(text: str = "Hello", font_size: float = 12.0) -> MagicMock:
    page = MagicMock()
    page.number = 0
    page.get_text.return_value = text
    page.get_text.side_effect = lambda *args, **kwargs: {
        ("text",): text,
        ("dict",): {
            "blocks": [
                {
                    "type": 0,
                    "bbox": (0, 0, 100, 20),
                    "lines": [
                        {
                            "spans": [
                                {
                                    "text": text,
                                    "size": font_size,
                                    "font": "Arial",
                                    "flags": 0,
                                }
                            ]
                        }
                    ],
                }
            ]
        },
        ("words",): [["w", 0, 0, 10, 10]],
    }.get(args, "")
    page.get_images.return_value = []
    page.get_links.return_value = []
    return page


def _make_fake_doc(pages: list[MagicMock] | None = None) -> MagicMock:
    doc = MagicMock()
    doc.__enter__ = lambda self: doc
    doc.__exit__ = lambda self, *args: None
    doc.is_encrypted = False
    doc.page_count = len(pages) if pages else 1
    doc.metadata = {
        "title": "T",
        "author": "A",
        "creationDate": "2024-01-01",
    }
    doc.load_page.side_effect = lambda i: pages[i] if pages else _make_fake_page()
    return doc


class TestPyMuPdfExtractorMetadata:
    def test_engine_is_pymupdf(self) -> None:
        assert PyMuPdfExtractor().engine.value == "pymupdf"


class TestPyMuPdfExtractorErrors:
    def test_missing_file_raises_corrupted(self, tmp_path: Path) -> None:
        with pytest.raises(CorruptedPdfError):
            PyMuPdfExtractor().extract(tmp_path / "nope.pdf")

    def test_encrypted_pdf_raises(self, tmp_path: Path) -> None:
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        doc = MagicMock()
        doc.__enter__ = lambda self: doc
        doc.__exit__ = lambda self, *args: None
        doc.is_encrypted = True
        doc.authenticate.return_value = False

        with patch("pdf2md.infrastructure.extractors.pymupdf_extractor.fitz") as fitz:
            fitz.open.return_value = doc
            with pytest.raises(EncryptedPdfError):
                PyMuPdfExtractor().extract(pdf)


class TestPyMuPdfExtractorHappyPath:
    def test_extracts_pages_with_blocks(self, tmp_path: Path) -> None:
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4")

        page = _make_fake_page("Body", font_size=12.0)
        doc = _make_fake_doc([page])

        with patch("pdf2md.infrastructure.extractors.pymupdf_extractor.fitz") as fitz:
            fitz.open.return_value = doc
            extracted = PyMuPdfExtractor().extract(pdf)

        assert extracted.page_count == 1
        assert extracted.metadata.title == "T"
        assert len(extracted.pages) == 1
        assert extracted.pages[0].raw_text == "Body"

    def test_skips_images_when_disabled(self, tmp_path: Path) -> None:
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        page = _make_fake_page("x")
        page.get_images.return_value = [(1, 0, 0, 0, 0, 0, 0)]  # one xref
        doc = _make_fake_doc([page])

        with patch("pdf2md.infrastructure.extractors.pymupdf_extractor.fitz") as fitz:
            fitz.open.return_value = doc
            extracted = PyMuPdfExtractor(
                config=ConversionConfig(extract_images=False)
            ).extract(pdf)

        assert extracted.pages[0].images == []


class TestPyMuPdfExtractorLinks:
    def test_uri_link(self, tmp_path: Path) -> None:
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        page = _make_fake_page("hi")
        page.get_links.return_value = [
            {"kind": 2, "uri": "https://example.com", "from": None},
        ]
        doc = _make_fake_doc([page])

        with patch("pdf2md.infrastructure.extractors.pymupdf_extractor.fitz") as fitz:
            fitz.LINK_URI = 2
            fitz.LINK_GOTO = 1
            fitz.open.return_value = doc
            links = PyMuPdfExtractor().extract_links(pdf)

        assert len(links) == 1
        assert links[0].url == "https://example.com"
        assert links[0].is_internal is False

    def test_internal_goto_link(self, tmp_path: Path) -> None:
        pdf = tmp_path / "x.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        page = _make_fake_page("hi")
        page.get_links.return_value = [
            {"kind": 1, "page": 4, "from": None},
        ]
        doc = _make_fake_doc([page])

        with patch("pdf2md.infrastructure.extractors.pymupdf_extractor.fitz") as fitz:
            fitz.LINK_URI = 2
            fitz.LINK_GOTO = 1
            fitz.open.return_value = doc
            links = PyMuPdfExtractor().extract_links(pdf)

        assert links[0].is_internal is True
        assert links[0].url == "#page-5"


class TestBulletRegex:
    """The _LIST_RE regex covers all bullet variants."""

    def test_bullet_matches(self) -> None:
        from pdf2md.infrastructure.extractors.pymupdf_extractor import _LIST_RE
        assert _LIST_RE.match("• Item")
        assert _LIST_RE.match("- Item")
        assert _LIST_RE.match("* Item")
        assert _LIST_RE.match("● Item")

    def test_bullet_alone_does_not_match(self) -> None:
        from pdf2md.infrastructure.extractors.pymupdf_extractor import _LIST_RE
        assert not _LIST_RE.match("●")
        assert not _LIST_RE.match("-")


class TestBuildDefaultTableExtractor:
    def test_default_table_extractor_is_scoped_pdfplumber(self) -> None:
        ext = build_default_table_extractor(TableEngine.PDFPLUMBER)
        assert type(ext).__name__ == "DocumentScopedTableExtractor"

    def test_camelot_table_extractor(self) -> None:
        ext = build_default_table_extractor(TableEngine.CAMELOT)
        assert type(ext).__name__ == "DocumentScopedTableExtractor"

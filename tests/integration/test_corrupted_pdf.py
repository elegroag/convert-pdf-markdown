"""Integration test: corrupted.pdf — malformed PDF handling."""

from __future__ import annotations

import pytest

from pdf2md.domain.exceptions import CorruptedPdfError
from pdf2md.infrastructure.extractors.pymupdf_extractor import PyMuPdfExtractor


class TestCorruptedPdf:
    def test_extract_raises_corrupted_error(self, pdf_path) -> None:
        path = pdf_path("corrupted.pdf")
        extractor = PyMuPdfExtractor()
        with pytest.raises(CorruptedPdfError):
            extractor.extract(path)

    def test_error_message_includes_filename(self, pdf_path) -> None:
        path = pdf_path("corrupted.pdf")
        extractor = PyMuPdfExtractor()
        with pytest.raises(CorruptedPdfError) as exc:
            extractor.extract(path)
        assert "corrupted" in str(exc.value).lower()

    def test_missing_file_also_raises_corrupted(self, tmp_path) -> None:
        path = tmp_path / "nonexistent.pdf"
        extractor = PyMuPdfExtractor()
        with pytest.raises(CorruptedPdfError):
            extractor.extract(path)

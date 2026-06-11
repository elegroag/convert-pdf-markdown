"""Integration test: encrypted.pdf — password-protected PDF handling."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from pdf2md.domain.exceptions import EncryptedPdfError
from pdf2md.infrastructure.extractors.pymupdf_extractor import PyMuPdfExtractor


class TestEncryptedPdf:
    """Extracting an encrypted PDF without a password raises EncryptedPdfError."""

    def test_extract_without_password_raises(
        self, pdf_path
    ) -> None:
        path = pdf_path("encrypted.pdf")
        extractor = PyMuPdfExtractor()
        with pytest.raises(EncryptedPdfError):
            extractor.extract(path)

    def test_extract_with_correct_password_succeeds(
        self, pdf_path, tmp_path
    ) -> None:
        """Open with PyMuPDF directly using the password."""
        import fitz
        path = pdf_path("encrypted.pdf")
        doc = fitz.open(str(path))
        assert doc.is_encrypted
        authenticated = doc.authenticate("secret")
        assert authenticated
        assert doc.page_count == 1
        text = doc[0].get_text("text")
        assert "Secret Document" in text
        doc.close()

    def test_wrong_password_fails(self, pdf_path) -> None:
        path = pdf_path("encrypted.pdf")
        import fitz
        doc = fitz.open(str(path))
        assert doc.is_encrypted
        authenticated = doc.authenticate("wrong")
        assert not authenticated
        doc.close()

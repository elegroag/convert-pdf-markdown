"""Tests for the pdfplumber and camelot table extractors.

The tests use mocks of the underlying libraries to avoid creating real
PDFs (real-PDF coverage is in the integration suite).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pdf2md.domain.exceptions import TableExtractionError
from pdf2md.infrastructure.extractors.camelot_extractor import (
    CamelotTableExtractor,
)
from pdf2md.infrastructure.extractors.pdfplumber_extractor import (
    PdfplumberTableExtractor,
    _sanitize_cell,
)


class TestSanitizeCell:
    """The cell sanitizer must produce GFM-safe content."""

    def test_none_becomes_empty_string(self) -> None:
        """None is rendered as an empty cell."""
        assert _sanitize_cell(None) == ""

    def test_pipe_is_escaped(self) -> None:
        """A literal ``|`` becomes ``\\|``."""
        assert _sanitize_cell("a|b") == "a\\|b"

    def test_newline_becomes_space(self) -> None:
        """A newline becomes a single space."""
        assert _sanitize_cell("a\nb") == "a b"

    def test_crlf_becomes_space(self) -> None:
        """A Windows line ending becomes a single space."""
        assert _sanitize_cell("a\r\nb") == "a b"

    def test_strip_whitespace(self) -> None:
        """Leading and trailing whitespace is stripped."""
        assert _sanitize_cell("  a  ") == "a"


class TestPdfplumberTableExtractor:
    """The pdfplumber extractor opens a PDF, finds tables, returns nodes."""

    def _mock_page(self, raw_tables: list) -> MagicMock:
        page = MagicMock()
        page.find_tables.return_value = raw_tables
        return page

    def _mock_pdf(self, pages: list) -> MagicMock:
        pdf = MagicMock()
        pdf.pages = pages
        pdf.__enter__ = MagicMock(return_value=pdf)
        pdf.__exit__ = MagicMock(return_value=False)
        return pdf

    def test_empty_table_list_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """A page with no tables yields an empty list."""
        raw = MagicMock()
        raw.extract.return_value = []
        page = self._mock_page([raw])
        pdf = self._mock_pdf([page])
        with patch(
            "pdf2md.infrastructure.extractors.pdfplumber_extractor.pdfplumber.open",
            return_value=pdf,
        ):
            out = PdfplumberTableExtractor().extract_tables(
                tmp_path / "x.pdf", 1
            )
        assert out == []

    def test_page_out_of_range_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """A page number beyond the document returns []."""
        page = self._mock_page([])
        pdf = self._mock_pdf([page])
        with patch(
            "pdf2md.infrastructure.extractors.pdfplumber_extractor.pdfplumber.open",
            return_value=pdf,
        ):
            out = PdfplumberTableExtractor().extract_tables(
                tmp_path / "x.pdf", 99
            )
        assert out == []

    def test_table_with_headers_and_rows(
        self, tmp_path: Path
    ) -> None:
        """A table with all-non-empty first row uses it as headers."""
        raw = MagicMock()
        raw.extract.return_value = [["H1", "H2"], ["v1", "v2"], ["v3", "v4"]]
        raw.bbox = (0, 0, 100, 200)
        page = self._mock_page([raw])
        pdf = self._mock_pdf([page])
        with patch(
            "pdf2md.infrastructure.extractors.pdfplumber_extractor.pdfplumber.open",
            return_value=pdf,
        ):
            out = PdfplumberTableExtractor().extract_tables(
                tmp_path / "x.pdf", 1
            )
        assert len(out) == 1
        assert out[0].headers == ["H1", "H2"]
        assert out[0].rows == [["v1", "v2"], ["v3", "v4"]]
        assert out[0].extraction_method == "pdfplumber"

    def test_table_without_headers_uses_fallback_names(
        self, tmp_path: Path
    ) -> None:
        """A table with empty first row gets ``col1``, ``col2`` headers."""
        raw = MagicMock()
        raw.extract.return_value = [["", ""], ["x", "y"]]
        raw.bbox = (0, 0, 100, 200)
        page = self._mock_page([raw])
        pdf = self._mock_pdf([page])
        with patch(
            "pdf2md.infrastructure.extractors.pdfplumber_extractor.pdfplumber.open",
            return_value=pdf,
        ):
            out = PdfplumberTableExtractor().extract_tables(
                tmp_path / "x.pdf", 1
            )
        assert out[0].headers == ["col1", "col2"]
        assert out[0].rows == [["", ""], ["x", "y"]]

    def test_table_with_pipes_escaped(
        self, tmp_path: Path
    ) -> None:
        """Pipe characters in cells are escaped."""
        raw = MagicMock()
        raw.extract.return_value = [["A|B", "C"]]
        raw.bbox = (0, 0, 100, 200)
        page = self._mock_page([raw])
        pdf = self._mock_pdf([page])
        with patch(
            "pdf2md.infrastructure.extractors.pdfplumber_extractor.pdfplumber.open",
            return_value=pdf,
        ):
            out = PdfplumberTableExtractor().extract_tables(
                tmp_path / "x.pdf", 1
            )
        assert out[0].headers == ["A\\|B", "C"]
        assert out[0].rows == []

    def test_empty_table_extraction_returns_empty_list(
        self, tmp_path: Path
    ) -> None:
        """A raw.extract() returning [] yields no TableNode."""
        raw = MagicMock()
        raw.extract.return_value = []
        page = self._mock_page([raw])
        pdf = self._mock_pdf([page])
        with patch(
            "pdf2md.infrastructure.extractors.pdfplumber_extractor.pdfplumber.open",
            return_value=pdf,
        ):
            out = PdfplumberTableExtractor().extract_tables(
                tmp_path / "x.pdf", 1
            )
        assert out == []

    def test_pdfplumber_open_failure_raises(
        self, tmp_path: Path
    ) -> None:
        """An exception from pdfplumber becomes TableExtractionError."""
        with patch(
            "pdf2md.infrastructure.extractors.pdfplumber_extractor.pdfplumber.open",
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(TableExtractionError):
                PdfplumberTableExtractor().extract_tables(
                    tmp_path / "x.pdf", 1
                )

    def test_individual_table_failure_is_skipped(
        self, tmp_path: Path
    ) -> None:
        """A failure in one table does not stop processing of others."""
        raw1 = MagicMock()
        raw1.extract.side_effect = RuntimeError("nope")
        raw1.bbox = (0, 0, 100, 200)
        raw2 = MagicMock()
        raw2.extract.return_value = [["A"], ["1"]]
        raw2.bbox = (0, 0, 100, 200)
        page = self._mock_page([raw1, raw2])
        pdf = self._mock_pdf([page])
        with patch(
            "pdf2md.infrastructure.extractors.pdfplumber_extractor.pdfplumber.open",
            return_value=pdf,
        ):
            out = PdfplumberTableExtractor().extract_tables(
                tmp_path / "x.pdf", 1
            )
        assert len(out) == 1
        assert out[0].headers == ["A"]


class TestCamelotTableExtractor:
    """The Camelot extractor is optional; tests cover the no-camelot path."""

    def test_invalid_flavor_raises(self) -> None:
        """An unknown flavor raises ValueError at construction."""
        with pytest.raises(ValueError):
            CamelotTableExtractor(flavor="bogus")

    def test_camelot_not_installed_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If camelot isn't installed, the extractor returns []."""
        import pdf2md.infrastructure.extractors.camelot_extractor as mod

        monkeypatch.setattr(mod, "camelot", None)
        out = CamelotTableExtractor().extract_tables(tmp_path / "x.pdf", 1)
        assert out == []

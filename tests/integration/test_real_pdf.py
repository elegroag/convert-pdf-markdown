"""Integration test: round-trip a real PDF.

Generates a PDF with PyMuPDF and exercises the full extraction +
rendering + storage pipeline. This validates the wiring between the
infrastructure adapters and the application service.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # type: ignore[import-not-found]
import pytest

from pdf2md.application.dto.dtos import ConversionRequest
from pdf2md.config.service_factory import build_default_service


def _make_pdf(path: Path) -> None:
    """Create a tiny 2-page PDF with text and metadata using PyMuPDF."""
    doc = fitz.open()
    page1 = doc.new_page(width=400, height=600)
    page1.insert_text(
        (50, 80),
        "Chapter 1",
        fontsize=22,
    )
    page1.insert_text(
        (50, 120),
        "This is a paragraph on the first page.",
        fontsize=12,
    )
    page1.insert_text((50, 160), "- item one", fontsize=12)
    page1.insert_text((50, 180), "- item two", fontsize=12)

    page2 = doc.new_page(width=400, height=600)
    page2.insert_text((50, 80), "Chapter 2", fontsize=22)
    page2.insert_text(
        (50, 120),
        "Second page content with some longer text.",
        fontsize=12,
    )

    doc.set_metadata(
        {
            "title": "Test Book",
            "author": "Test Author",
            "subject": "Integration",
            "creationDate": "2026-06-05",
        }
    )
    doc.save(str(path))
    doc.close()


class TestEndToEndConversion:
    """Convert a generated PDF and verify the output on disk."""

    def test_pdf_to_markdown_round_trip(self, tmp_path: Path) -> None:
        """A real PDF produces a Markdown file with frontmatter and headings."""
        pdf_path = tmp_path / "book.pdf"
        _make_pdf(pdf_path)
        out_dir = tmp_path / "out"
        service = build_default_service(output_dir=out_dir)

        result = service.convert(
            ConversionRequest(
                pdf_path=pdf_path, output_dir=out_dir
            )
        )

        assert result.status == "success"
        assert result.output_path is not None
        assert result.output_path.is_file()
        assert result.page_count == 2

        body = result.output_path.read_text(encoding="utf-8")
        assert "---" in body  # frontmatter
        assert "Test Book" in body
        assert "Test Author" in body
        assert "Chapter 1" in body
        assert "Chapter 2" in body

    def test_assets_directory_created(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An ``assets/`` directory is created (even if empty for text-only PDFs)."""
        pdf_path = tmp_path / "no_images.pdf"
        _make_pdf(pdf_path)
        out_dir = tmp_path / "out"
        service = build_default_service(output_dir=out_dir)

        result = service.convert(
            ConversionRequest(pdf_path=pdf_path, output_dir=out_dir)
        )
        assert result.status == "success"
        # The text-only PDF has no images, so no assets are written.
        assert not (out_dir / "assets").exists() or not any(
            (out_dir / "assets").iterdir()
        )

    def test_inspect_returns_metadata(
        self, tmp_path: Path
    ) -> None:
        """``inspect`` reports the metadata and page count of a real PDF."""
        pdf_path = tmp_path / "meta.pdf"
        _make_pdf(pdf_path)
        service = build_default_service(output_dir=tmp_path / "out")
        info = service.inspect(pdf_path)

        assert info.page_count == 2
        assert info.metadata["title"] == "Test Book"
        assert info.metadata["author"] == "Test Author"

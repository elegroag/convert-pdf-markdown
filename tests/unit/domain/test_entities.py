"""Tests for PdfDocument, PdfPage, ImageAsset, TableNode, MarkdownDocument."""

from __future__ import annotations

from pathlib import Path

from pdf2md.domain.entities.entities import (
    ImageAsset,
    MarkdownDocument,
    MarkdownPage,
    PdfDocument,
    PdfMetadata,
    PdfPage,
    TableNode,
)
from pdf2md.domain.value_objects.value_objects import ContentBlock


def _make_page(num: int) -> PdfPage:
    return PdfPage(
        page_number=num,
        raw_text=f"Page {num}",
        blocks=[ContentBlock(block_type="paragraph", text=f"para {num}")],
    )


class TestPdfMetadata:
    """Tests for :class:`PdfMetadata`."""

    def test_is_empty_when_all_blank(self) -> None:
        """All-blank metadata reports as empty."""
        assert PdfMetadata().is_empty() is True

    def test_is_not_empty_with_title(self) -> None:
        """A title makes the metadata non-empty."""
        assert PdfMetadata(title="Book").is_empty() is False


class TestPdfDocument:
    """Tests for :class:`PdfDocument`."""

    def test_iter_pages_returns_all(self) -> None:
        """No filter returns the entire page list in order."""
        doc = PdfDocument(
            file_path=Path("x.pdf"),
            page_count=3,
            pages=[_make_page(1), _make_page(2), _make_page(3)],
        )
        result = doc.iter_pages()
        assert [p.page_number for p in result] == [1, 2, 3]

    def test_iter_pages_with_dash_range(self) -> None:
        """Dash range ``1-2`` returns pages 1 and 2."""
        doc = PdfDocument(
            file_path=Path("x.pdf"),
            page_count=3,
            pages=[_make_page(1), _make_page(2), _make_page(3)],
        )
        result = doc.iter_pages("1-2")
        assert [p.page_number for p in result] == [1, 2]

    def test_iter_pages_with_comma_list(self) -> None:
        """Comma list ``1,3`` returns pages 1 and 3."""
        doc = PdfDocument(
            file_path=Path("x.pdf"),
            page_count=3,
            pages=[_make_page(1), _make_page(2), _make_page(3)],
        )
        result = doc.iter_pages("1,3")
        assert [p.page_number for p in result] == [1, 3]

    def test_iter_pages_with_open_ended_range(self) -> None:
        """Open-ended range ``2-`` returns from 2 to the end."""
        doc = PdfDocument(
            file_path=Path("x.pdf"),
            page_count=3,
            pages=[_make_page(1), _make_page(2), _make_page(3)],
        )
        result = doc.iter_pages("2-")
        assert [p.page_number for p in result] == [2, 3]


class TestImageAsset:
    """Tests for :class:`ImageAsset`."""

    def test_construction(self) -> None:
        """An image can be created with the minimum required data."""
        asset = ImageAsset(
            image_id="p1_img1",
            page_number=1,
            bbox=(0.0, 0.0, 100.0, 100.0),
            format="PNG",
            raw_bytes=b"\x89PNG",
        )
        assert asset.output_path is None
        assert asset.caption is None
        assert asset.raw_bytes == b"\x89PNG"


class TestTableNode:
    """Tests for :class:`TableNode`."""

    def test_construction(self) -> None:
        """A table holds headers and rows in order."""
        table = TableNode(
            page_number=2,
            bbox=(0.0, 0.0, 100.0, 200.0),
            headers=["A", "B"],
            rows=[["1", "2"], ["3", "4"]],
            extraction_method="pdfplumber",
        )
        assert table.headers == ["A", "B"]
        assert table.rows == [["1", "2"], ["3", "4"]]


class TestMarkdownDocument:
    """Tests for :class:`MarkdownDocument`."""

    def test_to_string_with_frontmatter(self) -> None:
        """Frontmatter is prepended to the rendered pages."""
        doc = MarkdownDocument(
            source_pdf=Path("x.pdf"),
            pages=[MarkdownPage(page_number=1, content="# Title")],
            frontmatter="---\ntitle: x\n---\n",
        )
        output = doc.to_string()
        assert output.startswith("---\n")
        assert "# Title" in output

    def test_to_string_empty_pages(self) -> None:
        """An empty pages list produces a document with only the frontmatter."""
        doc = MarkdownDocument(
            source_pdf=Path("x.pdf"), frontmatter="---\ntitle: x\n---\n"
        )
        assert doc.to_string().strip() == "---\ntitle: x\n---"

"""Tests for the HTML renderer."""

from __future__ import annotations

from pathlib import Path

from pdf2md.domain.entities.entities import (
    ImageAsset,
    PdfDocument,
    PdfMetadata,
    PdfPage,
    TableNode,
)
from pdf2md.domain.value_objects.value_objects import (
    ConversionConfig,
    ContentBlock,
    Link,
)
from pdf2md.infrastructure.renderers.html_renderer import HtmlRenderer


def _doc(**kwargs) -> PdfDocument:
    return PdfDocument(
        file_path=kwargs.pop("file_path", Path("book.pdf")),
        page_count=kwargs.pop("page_count", 1),
        metadata=kwargs.pop("metadata", PdfMetadata(title="T")),
        pages=kwargs.pop(
            "pages",
            [PdfPage(page_number=1, blocks=[ContentBlock("paragraph", "hi")])],
        ),
    )


class TestHtmlRenderer:
    """HtmlRenderer wraps the Markdown into a minimal HTML page."""

    def test_basic_structure(self) -> None:
        out = HtmlRenderer().render(_doc())
        body = out.pages[0].content
        assert body.startswith("<!DOCTYPE html>")
        assert "<html>" in body
        assert "<head>" in body
        assert "<body>" in body
        assert "</html>" in body

    def test_includes_title(self) -> None:
        out = HtmlRenderer().render(_doc(metadata=PdfMetadata(title="MyBook")))
        body = out.pages[0].content
        assert "<title>MyBook</title>" in body
        assert "MyBook" in body

    def test_escapes_html_in_title(self) -> None:
        out = HtmlRenderer().render(_doc(metadata=PdfMetadata(title="<script>")))
        body = out.pages[0].content
        assert "<script>" not in body.split("</title>")[0].split("<title>")[1]

    def test_renders_heading_block(self) -> None:
        doc = _doc(
            pages=[
                PdfPage(
                    page_number=1,
                    blocks=[ContentBlock("heading", "Big", font_size=24.0, level=1)],
                )
            ]
        )
        out = HtmlRenderer().render(doc)
        assert "<h1>Big</h1>" in out.pages[0].content

    def test_renders_paragraph(self) -> None:
        doc = _doc(
            pages=[
                PdfPage(
                    page_number=1,
                    blocks=[ContentBlock("paragraph", "Hello world")],
                )
            ]
        )
        out = HtmlRenderer().render(doc)
        assert "<p>Hello world</p>" in out.pages[0].content

    def test_renders_code_block_as_fenced_preformatted(self) -> None:
        doc = _doc(
            pages=[
                PdfPage(
                    page_number=1,
                    blocks=[ContentBlock("code", "print(1)")],
                )
            ]
        )
        out = HtmlRenderer().render(doc)
        body = out.pages[0].content
        # The HTML renderer keeps Markdown code fences verbatim rather
        # than translating them, by design.
        assert "```" in body
        assert "print(1)" in body

    def test_renders_table_rows_as_paragraphs(self) -> None:
        """Tables are not translated — the renderer is intentionally minimal."""
        doc = _doc(
            pages=[
                PdfPage(
                    page_number=1,
                    tables=[
                        TableNode(
                            page_number=1,
                            bbox=(0, 0, 10, 10),
                            headers=["A"],
                            rows=[["1"]],
                        )
                    ],
                )
            ]
        )
        out = HtmlRenderer().render(doc)
        body = out.pages[0].content
        # The Markdown table is wrapped in <p> per line, no <table>.
        assert "<table>" not in body
        assert "| A |" in body

    def test_renders_image(self) -> None:
        doc = _doc(
            pages=[
                PdfPage(
                    page_number=1,
                    images=[
                        ImageAsset(
                            image_id="p1_img1",
                            page_number=1,
                            bbox=(0, 0, 10, 10),
                            format="PNG",
                            raw_bytes=b"\x89PNG",
                            caption="My figure",
                        )
                    ],
                )
            ]
        )
        out = HtmlRenderer().render(doc)
        assert "<img" in out.pages[0].content
        assert 'alt="My figure"' in out.pages[0].content

    def test_renders_links_as_paragraphs(self) -> None:
        """When ``emit_link_list`` is on, inline link lists are emitted
        as ``<p>`` by the minimal HTML renderer. v0.2.0: opt-in only.
        """
        cfg = ConversionConfig(emit_link_list=True)
        doc = _doc(
            pages=[
                PdfPage(
                    page_number=1,
                    links=[Link(url="https://example.com", text="ex", page_number=1)],
                )
            ]
        )
        out = HtmlRenderer(cfg).render(doc)
        body = out.pages[0].content
        assert "<a " not in body
        assert "https://example.com" in body

    def test_falls_back_to_filename_title(self) -> None:
        out = HtmlRenderer().render(_doc(metadata=PdfMetadata(), file_path=Path("MyBook.pdf")))
        body = out.pages[0].content
        assert "<title>MyBook.pdf</title>" in body

    def test_handles_multiple_pages(self) -> None:
        doc = _doc(
            page_count=2,
            pages=[
                PdfPage(page_number=1, blocks=[ContentBlock("paragraph", "P1")]),
                PdfPage(page_number=2, blocks=[ContentBlock("paragraph", "P2")]),
            ],
        )
        out = HtmlRenderer().render(doc)
        body = out.pages[0].content
        assert "P1" in body
        assert "P2" in body

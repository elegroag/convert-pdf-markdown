"""Tests for the link-list rendering logic.

The renderer previously emitted a "URL dump" at the bottom of every
page. v0.2.0 makes it opt-in via ``ConversionConfig.emit_link_list``;
when on, the format becomes ``- [anchor text](url)`` and internal
links are filtered.
"""

from __future__ import annotations

from pdf2md.domain.entities.entities import (
    ImageAsset,
    MarkdownDocument,
    MarkdownPage,
    PdfDocument,
    PdfMetadata,
    PdfPage,
)
from pdf2md.domain.value_objects.enums import BlockType
from pdf2md.domain.value_objects.value_objects import (
    ConversionConfig,
    Link,
    ContentBlock,
)
from pdf2md.infrastructure.renderers.markdown_renderer import MarkdownRenderer


def _doc_with_links(links: list[Link]) -> PdfDocument:
    page = PdfPage(
        page_number=1,
        blocks=[ContentBlock(block_type="paragraph", text="Some body text.")],
        images=[],
        tables=[],
        links=links,
    )
    return PdfDocument(
        file_path=__import__("pathlib").Path("x.pdf"),
        page_count=1,
        metadata=PdfMetadata(title="T"),
        pages=[page],
    )


class TestEmitLinkListOff:
    def test_default_does_not_emit_link_dump(self) -> None:
        doc = _doc_with_links([
            Link(url="https://x.com", text="x", page_number=1, is_internal=False),
        ])
        out = MarkdownRenderer().render(doc)
        assert "https://x.com" not in out.pages[0].content
        # The body text is still present.
        assert "Some body text." in out.pages[0].content

    def test_internal_link_dump_absent_by_default(self) -> None:
        doc = _doc_with_links([
            Link(url="#page-2", text="next", page_number=1, is_internal=True),
        ])
        out = MarkdownRenderer().render(doc)
        assert "#page-2" not in out.pages[0].content


class TestEmitLinkListOn:
    def test_emits_anchor_text_with_url(self) -> None:
        doc = _doc_with_links([
            Link(url="https://x.com", text="X website", page_number=1, is_internal=False),
        ])
        cfg = ConversionConfig(emit_link_list=True)
        out = MarkdownRenderer(cfg).render(doc)
        assert "[X website](https://x.com)" in out.pages[0].content

    def test_falls_back_to_url_when_anchor_text_is_empty(self) -> None:
        doc = _doc_with_links([
            Link(url="https://x.com", text="", page_number=1, is_internal=False),
        ])
        cfg = ConversionConfig(emit_link_list=True)
        out = MarkdownRenderer(cfg).render(doc)
        assert "[https://x.com](https://x.com)" in out.pages[0].content

    def test_filters_internal_links(self) -> None:
        doc = _doc_with_links([
            Link(url="https://x.com", text="X", page_number=1, is_internal=False),
            Link(url="#page-2", text="next", page_number=1, is_internal=True),
        ])
        cfg = ConversionConfig(emit_link_list=True)
        out = MarkdownRenderer(cfg).render(doc)
        assert "[X](https://x.com)" in out.pages[0].content
        assert "#page-2" not in out.pages[0].content

    def test_no_links_means_no_section(self) -> None:
        doc = _doc_with_links([])
        cfg = ConversionConfig(emit_link_list=True)
        out = MarkdownRenderer(cfg).render(doc)
        # Body text present, no bullet list at the end.
        assert "Some body text." in out.pages[0].content

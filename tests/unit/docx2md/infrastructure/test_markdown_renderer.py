"""Tests for docx2md MarkdownRenderer."""

from __future__ import annotations

from docx2md.domain.entities.entities import (
    HeadingBlock,
    ImageBlock,
    ListItemBlock,
    ParagraphBlock,
    TableBlock,
)
from docx2md.infrastructure.renderers.markdown_renderer import MarkdownRenderer


class TestMarkdownRenderer:
    def test_renders_heading_and_paragraph(self) -> None:
        renderer = MarkdownRenderer()
        doc = renderer.render(
            [
                HeadingBlock(level=1, text="Title"),
                ParagraphBlock(text="Body text"),
            ]
        )
        assert "# Title" in doc.content
        assert "Body text" in doc.content

    def test_renders_table(self) -> None:
        renderer = MarkdownRenderer()
        doc = renderer.render([TableBlock(rows=[["A", "B"], ["1", "2"]])])
        assert "| A | B |" in doc.content
        assert "| --- | --- |" in doc.content

    def test_renders_list_item(self) -> None:
        renderer = MarkdownRenderer()
        doc = renderer.render([ListItemBlock(text="Item", ordered=False, level=0)])
        assert "- Item" in doc.content

    def test_renders_image(self) -> None:
        renderer = MarkdownRenderer()
        doc = renderer.render([ImageBlock(filename="assets/img.png", alt_text="pic")])
        assert "![pic](assets/img.png)" in doc.content

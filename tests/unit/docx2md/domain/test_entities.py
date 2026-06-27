"""Tests for docx2md domain entities."""

from __future__ import annotations

from pathlib import Path

from docx2md.domain.entities.entities import (
    DocxMetadata,
    HeadingBlock,
    MarkdownDocument,
    TableBlock,
)


class TestDocxMetadata:
    def test_is_empty_when_all_blank(self) -> None:
        assert DocxMetadata().is_empty() is True

    def test_is_not_empty_with_title(self) -> None:
        assert DocxMetadata(title="Doc").is_empty() is False


class TestDocumentBlocks:
    def test_heading_block_is_frozen(self) -> None:
        block = HeadingBlock(level=1, text="Title")
        assert block.level == 1
        assert block.text == "Title"

    def test_table_block_mutable_rows(self) -> None:
        block = TableBlock()
        block.rows.append(["a", "b"])
        assert block.rows == [["a", "b"]]


class TestMarkdownDocument:
    def test_to_string_with_frontmatter(self) -> None:
        doc = MarkdownDocument(
            source_docx=Path("test.docx"),
            content="# Hello\n",
            frontmatter="---\ntitle: Test\n---",
        )
        result = doc.to_string()
        assert "---" in result
        assert "# Hello" in result

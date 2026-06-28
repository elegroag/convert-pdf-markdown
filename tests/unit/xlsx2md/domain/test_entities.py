"""Tests for xlsx2md domain entities."""

from __future__ import annotations

from pathlib import Path

from xlsx2md.domain.entities.entities import (
    EmptySheet,
    HeadingBlock,
    ImageBlock,
    ImageSheet,
    KeyValueBlock,
    MarkdownDocument,
    NarrativeSheet,
    ParagraphBlock,
    TableBlock,
    TableSheet,
    XlsxMetadata,
)


class TestXlsxMetadata:
    def test_is_empty_when_all_blank(self) -> None:
        assert XlsxMetadata().is_empty() is True

    def test_is_not_empty_with_title(self) -> None:
        assert XlsxMetadata(title="Book").is_empty() is False


class TestTableBlock:
    def test_is_empty_without_rows(self) -> None:
        assert TableBlock().is_empty() is True


class TestNarrativeSheet:
    def test_row_count_sums_tables(self) -> None:
        sheet = NarrativeSheet(
            name="S",
            index=0,
            blocks=[
                HeadingBlock(text="T"),
                TableBlock(rows=[["a", "b"], ["1", "2"]]),
            ],
        )
        assert sheet.row_count == 2


class TestTableSheet:
    def test_row_count_sums_tables(self) -> None:
        sheet = TableSheet(
            name="S",
            index=0,
            tables=[TableBlock(rows=[["a"], ["1"]]), TableBlock(rows=[["x"], ["y"], ["z"]])],
        )
        assert sheet.row_count == 5


class TestImageSheet:
    def test_is_not_empty_with_images(self) -> None:
        sheet = ImageSheet(name="Logo", index=0, images=[ImageBlock(filename="logo.png")])
        assert sheet.is_empty() is False


class TestEmptySheet:
    def test_is_empty(self) -> None:
        assert EmptySheet(name="Vacia", index=0).is_empty() is True


class TestMarkdownDocument:
    def test_to_string_with_frontmatter(self) -> None:
        doc = MarkdownDocument(
            source_xlsx=Path("test.xlsx"),
            sheet_name="Resumen",
            content="# Resumen\n",
            frontmatter="---\ntitle: Test\n---",
        )
        result = doc.to_string()
        assert "---" in result
        assert "# Resumen" in result

"""Tests for Markdown and Index renderers."""

from __future__ import annotations

from pathlib import Path

from xlsx2md.domain.entities.entities import (
    HeadingBlock,
    ImageBlock,
    KeyValueBlock,
    NarrativeSheet,
    TableBlock,
    TableSheet,
    XlsxDocument,
    XlsxMetadata,
)
from xlsx2md.infrastructure.renderers.index_renderer import IndexRenderer
from xlsx2md.infrastructure.renderers.markdown_renderer import MarkdownRenderer


class TestMarkdownRenderer:
    def test_renders_narrative_with_keyvalue(self) -> None:
        sheet = NarrativeSheet(
            name="Informe",
            index=0,
            blocks=[
                KeyValueBlock(label="OBJETIVO", value="Evaluar el SGSI"),
                TableBlock(headers=["A", "B"], rows=[["1", "2"]]),
            ],
        )
        document = XlsxDocument(
            file_path=Path("book.xlsx"),
            sheets=[sheet],
            metadata=XlsxMetadata(title="Informe"),
        )
        markdown = MarkdownRenderer().render(document, sheet)

        assert "**OBJETIVO:** Evaluar el SGSI" in markdown.content
        assert "| A" in markdown.content

    def test_renders_table_sheet(self) -> None:
        sheet = TableSheet(
            name="Datos",
            index=0,
            tables=[TableBlock(headers=["Col1", "Col2"], rows=[["A", "B"]])],
        )
        document = XlsxDocument(file_path=Path("book.xlsx"), sheets=[sheet])
        markdown = MarkdownRenderer().render(document, sheet)

        assert "# Datos" in markdown.content
        assert "Col1" in markdown.content

    def test_renders_images(self) -> None:
        sheet = TableSheet(
            name="Imagenes",
            index=0,
            tables=[TableBlock(headers=["H"], rows=[["1"]])],
            images=[ImageBlock(filename="assets/img_001.png", alt_text="logo", anchor_cell="B2")],
        )
        document = XlsxDocument(file_path=Path("book.xlsx"), sheets=[sheet])
        markdown = MarkdownRenderer().render(document, sheet)

        assert "![logo](assets/img_001.png)" in markdown.content


class TestIndexRenderer:
    def test_renders_toc(self, tmp_path: Path) -> None:
        sheet = TableSheet(
            name="Datos",
            index=0,
            tables=[TableBlock(headers=["H"], rows=[["1"], ["2"]])],
        )
        document = XlsxDocument(
            file_path=Path("book.xlsx"),
            sheets=[sheet],
            metadata=XlsxMetadata(title="Libro"),
        )
        sheet_files = {"Datos": tmp_path / "datos.md"}
        markdown = IndexRenderer().render(document, sheet_files)

        assert "# Libro" in markdown.content
        assert "[Datos](datos.md)" in markdown.content
        assert "2 filas" in markdown.content

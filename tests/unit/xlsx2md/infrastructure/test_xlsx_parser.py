"""Tests for XlsxParser."""

from __future__ import annotations

from pathlib import Path

from xlsx2md.domain.entities.entities import (
    EmptySheet,
    ImageSheet,
    NarrativeSheet,
    TableSheet,
)
from xlsx2md.domain.value_objects.value_objects import ConversionConfig
from xlsx2md.infrastructure.parsers.xlsx_parser import XlsxParser
from tests.fixtures.xlsx_generator import (
    build_simple_xlsx,
    build_xlsx_multi_sheet,
    build_xlsx_with_formulas,
    build_xlsx_with_hyperlink,
    build_xlsx_with_merges,
    build_xlsx_with_narrative,
)


class TestXlsxParser:
    def test_parses_pure_table_as_table_sheet(self, tmp_path: Path) -> None:
        xlsx_path = build_simple_xlsx(tmp_path / "simple.xlsx")
        parser = XlsxParser(config=ConversionConfig(detect_blocks=True))
        document = parser.parse(Path(xlsx_path), book_dir=tmp_path / "book")

        assert document.file_path.name == "simple.xlsx"
        assert isinstance(document.sheets[0], TableSheet)
        assert len(document.sheets[0].tables[0].headers) == 4

    def test_parses_narrative_informe(self, tmp_path: Path) -> None:
        xlsx_path = build_xlsx_with_narrative(tmp_path / "informe.xlsx")
        parser = XlsxParser(config=ConversionConfig(detect_blocks=True))
        document = parser.parse(Path(xlsx_path), book_dir=tmp_path / "book")

        sheet = document.sheets[0]
        assert isinstance(sheet, NarrativeSheet)
        labels = {block.label for block in sheet.blocks if hasattr(block, "label")}
        assert "OBJETIVO" in labels

    def test_parses_formulas(self, tmp_path: Path) -> None:
        xlsx_path = build_xlsx_with_formulas(tmp_path / "formulas.xlsx")
        parser = XlsxParser()
        document = parser.parse(Path(xlsx_path), book_dir=tmp_path / "book")

        sheet = document.sheets[0]
        if isinstance(sheet, TableSheet):
            rendered = sheet.tables[0].rows
            formula_cells = [v for row in rendered for v in row if "=" in v]
            assert formula_cells, f"No formula cells in {rendered}"

    def test_parses_merged_cells(self, tmp_path: Path) -> None:
        xlsx_path = build_xlsx_with_merges(tmp_path / "merges.xlsx")
        parser = XlsxParser()
        document = parser.parse(Path(xlsx_path), book_dir=tmp_path / "book")

        if isinstance(document.sheets[0], TableSheet):
            headers = document.sheets[0].tables[0].headers
            assert headers[:3] == ["Encabezado combinado"] * 3

    def test_parses_hyperlinks(self, tmp_path: Path) -> None:
        xlsx_path = build_xlsx_with_hyperlink(tmp_path / "links.xlsx")
        parser = XlsxParser()
        document = parser.parse(Path(xlsx_path), book_dir=tmp_path / "book")

        sheet = document.sheets[0]
        if isinstance(sheet, TableSheet):
            row_str = " | ".join(sheet.tables[0].rows[0])
            assert "[Example](https://example.com)" in row_str

    def test_multi_sheet_detects_empty(self, tmp_path: Path) -> None:
        xlsx_path = build_xlsx_multi_sheet(tmp_path / "multi.xlsx")
        parser = XlsxParser()
        document = parser.parse(Path(xlsx_path), book_dir=tmp_path / "book")

        empty_sheet = next(s for s in document.sheets if s.name == "Vacia")
        assert isinstance(empty_sheet, EmptySheet)

    def test_detect_blocks_disabled_falls_back(self, tmp_path: Path) -> None:
        xlsx_path = build_simple_xlsx(tmp_path / "simple.xlsx")
        parser = XlsxParser(config=ConversionConfig(detect_blocks=False))
        document = parser.parse(Path(xlsx_path), book_dir=tmp_path / "book")

        assert isinstance(document.sheets[0], NarrativeSheet)

    def test_max_table_cols_truncates(self, tmp_path: Path) -> None:
        xlsx_path = build_simple_xlsx(tmp_path / "wide.xlsx", cols=20)
        parser = XlsxParser(config=ConversionConfig(default_table_max_cols=5))
        document = parser.parse(Path(xlsx_path), book_dir=tmp_path / "book")

        if isinstance(document.sheets[0], TableSheet):
            for row in document.sheets[0].tables[0].rows:
                assert len(row) <= 5

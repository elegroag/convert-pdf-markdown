"""Tests for DocxParser."""

from __future__ import annotations

from pathlib import Path

from docx2md.domain.entities.entities import HeadingBlock, ParagraphBlock, TableBlock
from docx2md.infrastructure.parsers.docx_parser import DocxParser
from docx2md.infrastructure.storage.asset_exporter import FileAssetExporter
from tests.fixtures.docx_generator import build_simple_docx


class TestDocxParser:
    def test_parses_heading_and_paragraph(self, tmp_path: Path) -> None:
        docx_path = build_simple_docx(tmp_path / "simple.docx")
        parser = DocxParser()
        blocks = list(parser.parse(Path(docx_path)))

        assert any(isinstance(b, HeadingBlock) for b in blocks)
        assert any(isinstance(b, ParagraphBlock) for b in blocks)
        assert any(isinstance(b, TableBlock) for b in blocks)

    def test_parses_with_asset_exporter(self, tmp_path: Path) -> None:
        docx_path = build_simple_docx(tmp_path / "simple.docx")
        assets_dir = tmp_path / "assets"
        exporter = FileAssetExporter(assets_dir=assets_dir)
        parser = DocxParser(asset_exporter=exporter)
        blocks = list(parser.parse(Path(docx_path)))
        assert len(blocks) > 0

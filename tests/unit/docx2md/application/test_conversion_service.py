"""Tests for docx2md ConversionService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from docx2md.application.dto.dtos import ConversionRequest
from docx2md.application.services.conversion_service import ConversionService
from docx2md.domain.entities.entities import HeadingBlock, ParagraphBlock
from docx2md.domain.use_cases.use_cases import ConvertDocumentResult


class TestConversionService:
    def test_convert_delegates_to_use_case(self, tmp_path: Path) -> None:
        parser = MagicMock()
        renderer = MagicMock()
        storage = MagicMock()
        parser.parse.return_value = iter(
            [HeadingBlock(level=1, text="T"), ParagraphBlock(text="p")]
        )

        service = ConversionService(parser, renderer, storage)
        service._use_case.execute = MagicMock(  # noqa: SLF001
            return_value=ConvertDocumentResult(
                status="success",
                output_path=tmp_path / "out.md",
                total_blocks=2,
                headings=1,
                paragraphs=1,
            )
        )

        result = service.convert(
            ConversionRequest(docx_path=tmp_path / "x.docx", output_dir=tmp_path)
        )
        assert result.status == "success"
        assert result.headings == 1

    def test_inspect_counts_blocks(self, tmp_path: Path) -> None:
        parser = MagicMock()
        parser.parse.return_value = iter(
            [
                HeadingBlock(level=1, text="T"),
                HeadingBlock(level=2, text="S"),
                ParagraphBlock(text="p"),
            ]
        )
        service = ConversionService(parser, MagicMock(), MagicMock())
        result = service.inspect(tmp_path / "x.docx")
        assert result.total_blocks == 3
        assert result.heading_counts == {1: 1, 2: 1}
        assert result.paragraph_count == 1

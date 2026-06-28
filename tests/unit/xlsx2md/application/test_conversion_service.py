"""Tests for ConversionService."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from xlsx2md.application.dto.dtos import ConversionRequest
from xlsx2md.application.services.conversion_service import ConversionService
from xlsx2md.domain.use_cases.use_cases import ConvertSpreadsheetResult


class TestConversionService:
    def test_convert_delegates_to_use_case(self, tmp_path: Path) -> None:
        parser = MagicMock()
        renderer = MagicMock()
        index_renderer = MagicMock()
        storage = MagicMock()
        service = ConversionService(parser, renderer, index_renderer, storage)
        service._use_case.execute = MagicMock(  # noqa: SLF001
            return_value=ConvertSpreadsheetResult(
                status="success",
                sheet_outputs=(tmp_path / "book" / "resumen.md",),
                total_sheets=1,
            )
        )

        result = service.convert(
            ConversionRequest(
                xlsx_path=tmp_path / "book.xlsx",
                output_dir=tmp_path,
            )
        )

        assert result.status == "success"
        assert result.total_sheets == 1

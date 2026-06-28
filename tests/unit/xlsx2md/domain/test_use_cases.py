"""Tests for ConvertSpreadsheetUseCase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from xlsx2md.domain.entities.entities import KeyValueBlock, MarkdownDocument, NarrativeSheet
from xlsx2md.domain.exceptions import ExtractionError, RenderingError, StorageError
from xlsx2md.domain.use_cases.use_cases import (
    ConvertSpreadsheetRequest,
    ConvertSpreadsheetUseCase,
)


@pytest.fixture
def mock_parser() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_renderer() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_index_renderer() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_storage() -> MagicMock:
    return MagicMock()


class TestConvertSpreadsheetUseCaseSuccess:
    def test_happy_path(
        self,
        mock_parser: MagicMock,
        mock_renderer: MagicMock,
        mock_index_renderer: MagicMock,
        mock_storage: MagicMock,
        tmp_path: Path,
    ) -> None:
        sheet = NarrativeSheet(
            name="Resumen",
            index=0,
            blocks=[KeyValueBlock(label="Titulo", value="Demo")],
        )
        document = MagicMock()
        document.sheets = [sheet]
        mock_parser.parse.return_value = document
        mock_renderer.render.return_value = MarkdownDocument(
            source_xlsx=tmp_path / "test.xlsx",
            sheet_name="Resumen",
            content="# Resumen\n",
        )
        mock_storage.save.side_effect = [
            tmp_path / "book" / "resumen.md",
            tmp_path / "book" / "_index.md",
        ]
        mock_index_renderer.render.return_value = MarkdownDocument(
            source_xlsx=tmp_path / "test.xlsx",
            sheet_name="_index",
            content="# Index\n",
        )

        use_case = ConvertSpreadsheetUseCase(
            mock_parser,
            mock_renderer,
            mock_index_renderer,
            mock_storage,
        )
        result = use_case.execute(
            ConvertSpreadsheetRequest(
                xlsx_path=tmp_path / "test.xlsx",
                output_dir=tmp_path,
            )
        )

        assert result.status == "success"
        assert len(result.sheet_outputs) == 1
        assert result.index_path == tmp_path / "book" / "_index.md"
        assert result.total_sheets == 1


class TestConvertSpreadsheetUseCaseFailure:
    def test_extraction_error(
        self,
        mock_parser: MagicMock,
        mock_renderer: MagicMock,
        mock_index_renderer: MagicMock,
        mock_storage: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_parser.parse.side_effect = ExtractionError("parse failed")
        use_case = ConvertSpreadsheetUseCase(
            mock_parser,
            mock_renderer,
            mock_index_renderer,
            mock_storage,
        )
        result = use_case.execute(
            ConvertSpreadsheetRequest(xlsx_path=tmp_path / "x.xlsx", output_dir=tmp_path)
        )
        assert result.status == "error"
        assert result.error == "ExtractionError"

    def test_rendering_error(
        self,
        mock_parser: MagicMock,
        mock_renderer: MagicMock,
        mock_index_renderer: MagicMock,
        mock_storage: MagicMock,
        tmp_path: Path,
    ) -> None:
        document = MagicMock()
        document.sheets = [
            NarrativeSheet(
                name="Resumen",
                index=0,
                blocks=[KeyValueBlock(label="X", value="Y")],
            )
        ]
        mock_parser.parse.return_value = document
        mock_renderer.render.side_effect = RenderingError("render failed")
        use_case = ConvertSpreadsheetUseCase(
            mock_parser,
            mock_renderer,
            mock_index_renderer,
            mock_storage,
        )
        result = use_case.execute(
            ConvertSpreadsheetRequest(xlsx_path=tmp_path / "x.xlsx", output_dir=tmp_path)
        )
        assert result.status == "error"
        assert result.error == "RenderingError"

    def test_storage_error(
        self,
        mock_parser: MagicMock,
        mock_renderer: MagicMock,
        mock_index_renderer: MagicMock,
        mock_storage: MagicMock,
        tmp_path: Path,
    ) -> None:
        document = MagicMock()
        document.sheets = [
            NarrativeSheet(
                name="Resumen",
                index=0,
                blocks=[KeyValueBlock(label="X", value="Y")],
            )
        ]
        mock_parser.parse.return_value = document
        mock_renderer.render.return_value = MarkdownDocument(
            source_xlsx=tmp_path / "x.xlsx",
            sheet_name="Resumen",
            content="# Resumen\n",
        )
        mock_storage.save.side_effect = StorageError("write failed")
        use_case = ConvertSpreadsheetUseCase(
            mock_parser,
            mock_renderer,
            mock_index_renderer,
            mock_storage,
        )
        result = use_case.execute(
            ConvertSpreadsheetRequest(xlsx_path=tmp_path / "x.xlsx", output_dir=tmp_path)
        )
        assert result.status == "error"
        assert result.error == "StorageError"

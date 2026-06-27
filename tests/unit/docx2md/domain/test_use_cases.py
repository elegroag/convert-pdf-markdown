"""Tests for ConvertDocumentUseCase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from docx2md.domain.entities.entities import (
    HeadingBlock,
    MarkdownDocument,
    ParagraphBlock,
)
from docx2md.domain.exceptions import ExtractionError, RenderingError, StorageError
from docx2md.domain.use_cases.use_cases import (
    ConvertDocumentRequest,
    ConvertDocumentUseCase,
)


@pytest.fixture
def mock_parser() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_renderer() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_storage() -> MagicMock:
    return MagicMock()


class TestConvertDocumentUseCaseSuccess:
    def test_happy_path(
        self,
        mock_parser: MagicMock,
        mock_renderer: MagicMock,
        mock_storage: MagicMock,
        tmp_path: Path,
    ) -> None:
        blocks = [HeadingBlock(level=1, text="Title"), ParagraphBlock(text="Body")]
        mock_parser.parse.return_value = iter(blocks)
        mock_renderer.render.return_value = MarkdownDocument(
            source_docx=tmp_path / "test.docx",
            content="# Title\n\nBody\n",
        )
        mock_storage.save.return_value = tmp_path / "test.md"

        use_case = ConvertDocumentUseCase(mock_parser, mock_renderer, mock_storage)
        result = use_case.execute(
            ConvertDocumentRequest(
                docx_path=tmp_path / "test.docx",
                output_dir=tmp_path,
            )
        )

        assert result.status == "success"
        assert result.output_path == tmp_path / "test.md"
        assert result.headings == 1
        assert result.paragraphs == 1
        mock_parser.parse.assert_called_once()
        mock_renderer.render.assert_called_once()
        mock_storage.save.assert_called_once()


class TestConvertDocumentUseCaseFailure:
    def test_extraction_error(
        self,
        mock_parser: MagicMock,
        mock_renderer: MagicMock,
        mock_storage: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_parser.parse.side_effect = ExtractionError("parse failed")
        use_case = ConvertDocumentUseCase(mock_parser, mock_renderer, mock_storage)
        result = use_case.execute(
            ConvertDocumentRequest(docx_path=tmp_path / "x.docx", output_dir=tmp_path)
        )
        assert result.status == "error"
        assert result.error == "ExtractionError"

    def test_rendering_error(
        self,
        mock_parser: MagicMock,
        mock_renderer: MagicMock,
        mock_storage: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_parser.parse.return_value = iter([])
        mock_renderer.render.side_effect = RenderingError("render failed")
        use_case = ConvertDocumentUseCase(mock_parser, mock_renderer, mock_storage)
        result = use_case.execute(
            ConvertDocumentRequest(docx_path=tmp_path / "x.docx", output_dir=tmp_path)
        )
        assert result.status == "error"
        assert result.error == "RenderingError"

    def test_storage_error(
        self,
        mock_parser: MagicMock,
        mock_renderer: MagicMock,
        mock_storage: MagicMock,
        tmp_path: Path,
    ) -> None:
        mock_parser.parse.return_value = iter([])
        mock_renderer.render.return_value = MarkdownDocument(
            source_docx=tmp_path / "x.docx", content=""
        )
        mock_storage.save.side_effect = StorageError("write failed")
        use_case = ConvertDocumentUseCase(mock_parser, mock_renderer, mock_storage)
        result = use_case.execute(
            ConvertDocumentRequest(docx_path=tmp_path / "x.docx", output_dir=tmp_path)
        )
        assert result.status == "error"
        assert result.error == "StorageError"

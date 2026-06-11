"""Tests for ConvertPdfUseCase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pdf2md.domain.entities.entities import (
    ImageAsset,
    MarkdownDocument,
    MarkdownPage,
    PdfDocument,
    PdfPage,
    TableNode,
)
from pdf2md.domain.exceptions import (
    CorruptedPdfError,
    EncryptedPdfError,
    ExtractionError,
    RenderingError,
    StorageError,
)
from pdf2md.domain.ports.ports import IExtractor, IRenderer, IStorage
from pdf2md.domain.use_cases.use_cases import (
    ConvertPdfRequest,
    ConvertPdfResult,
    ConvertPdfUseCase,
)
from pdf2md.domain.value_objects.value_objects import ConversionConfig


def _build_pdf(page_count: int = 1) -> PdfDocument:
    pages = [
        PdfPage(
            page_number=i + 1,
            images=[
                ImageAsset(
                    image_id=f"p{i + 1}_img1",
                    page_number=i + 1,
                    bbox=(0, 0, 10, 10),
                    format="PNG",
                    raw_bytes=b"\x89PNG",
                )
            ],
            tables=[
                TableNode(
                    page_number=i + 1,
                    bbox=(0, 0, 10, 10),
                    headers=["a"],
                    rows=[["b"]],
                )
            ],
        )
        for i in range(page_count)
    ]
    return PdfDocument(file_path=Path("x.pdf"), page_count=page_count, pages=pages)


def _build_md() -> MarkdownDocument:
    return MarkdownDocument(
        source_pdf=Path("x.pdf"),
        pages=[MarkdownPage(page_number=1, content="# x")],
    )


class TestConvertPdfUseCaseSuccess:
    """The use case orchestrates extract → render → save on the happy path."""

    def test_calls_each_port_once(
        self,
        mock_extractor: MagicMock,
        mock_renderer: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """Extractor, renderer, and storage are each called once with order."""
        pdf = _build_pdf()
        md = _build_md()
        mock_extractor.extract.return_value = pdf
        mock_renderer.render.return_value = md
        mock_storage.save.return_value = Path("/out/x.md")

        use_case = ConvertPdfUseCase(
            mock_extractor, mock_renderer, mock_storage
        )
        result = use_case.execute(
            ConvertPdfRequest(pdf_path=Path("x.pdf"), output_dir=Path("/out"))
        )

        mock_extractor.extract.assert_called_once_with(Path("x.pdf"))
        mock_renderer.render.assert_called_once_with(pdf)
        mock_storage.save.assert_called_once_with(md, source=pdf)
        assert result.status == "success"
        assert result.output_path == Path("/out/x.md")
        assert result.page_count == 1
        assert result.image_count == 1
        assert result.table_count == 1

    def test_returns_counts_aggregated_across_pages(
        self,
        mock_extractor: MagicMock,
        mock_renderer: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """Image and table counts aggregate across all pages."""
        mock_extractor.extract.return_value = _build_pdf(page_count=3)
        mock_renderer.render.return_value = _build_md()
        mock_storage.save.return_value = Path("/o.md")

        result = ConvertPdfUseCase(
            mock_extractor, mock_renderer, mock_storage
        ).execute(ConvertPdfRequest(pdf_path=Path("x"), output_dir=Path("/o")))

        assert result.page_count == 3
        assert result.image_count == 3
        assert result.table_count == 3


class TestConvertPdfUseCaseFailures:
    """Domain exceptions surface as a failure result, not a crash."""

    def test_encrypted_pdf_returns_failure(
        self,
        mock_extractor: MagicMock,
        mock_renderer: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """EncryptedPdfError becomes a failure result."""
        mock_extractor.extract.side_effect = EncryptedPdfError("locked")
        use_case = ConvertPdfUseCase(
            mock_extractor, mock_renderer, mock_storage
        )
        result = use_case.execute(
            ConvertPdfRequest(pdf_path=Path("x"), output_dir=Path("/o"))
        )
        assert result.status == "error"
        assert result.error == "EncryptedPdfError"
        assert "locked" in result.error_message

    def test_corrupted_pdf_returns_failure(
        self,
        mock_extractor: MagicMock,
        mock_renderer: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """CorruptedPdfError becomes a failure result."""
        mock_extractor.extract.side_effect = CorruptedPdfError("bad")
        use_case = ConvertPdfUseCase(
            mock_extractor, mock_renderer, mock_storage
        )
        result = use_case.execute(
            ConvertPdfRequest(pdf_path=Path("x"), output_dir=Path("/o"))
        )
        assert result.status == "error"
        assert result.error == "CorruptedPdfError"

    def test_extraction_error_returns_failure(
        self,
        mock_extractor: MagicMock,
        mock_renderer: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """Generic ExtractionError becomes a failure result."""
        mock_extractor.extract.side_effect = ExtractionError("nope")
        use_case = ConvertPdfUseCase(
            mock_extractor, mock_renderer, mock_storage
        )
        result = use_case.execute(
            ConvertPdfRequest(pdf_path=Path("x"), output_dir=Path("/o"))
        )
        assert result.status == "error"
        assert result.error == "ExtractionError"

    def test_rendering_error_returns_failure(
        self,
        mock_extractor: MagicMock,
        mock_renderer: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """RenderingError becomes a failure result."""
        mock_extractor.extract.return_value = _build_pdf()
        mock_renderer.render.side_effect = RenderingError("oops")
        use_case = ConvertPdfUseCase(
            mock_extractor, mock_renderer, mock_storage
        )
        result = use_case.execute(
            ConvertPdfRequest(pdf_path=Path("x"), output_dir=Path("/o"))
        )
        assert result.status == "error"
        assert result.error == "RenderingError"

    def test_storage_error_returns_failure(
        self,
        mock_extractor: MagicMock,
        mock_renderer: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """StorageError becomes a failure result."""
        mock_extractor.extract.return_value = _build_pdf()
        mock_renderer.render.return_value = _build_md()
        mock_storage.save.side_effect = StorageError("disk full")
        use_case = ConvertPdfUseCase(
            mock_extractor, mock_renderer, mock_storage
        )
        result = use_case.execute(
            ConvertPdfRequest(pdf_path=Path("x"), output_dir=Path("/o"))
        )
        assert result.status == "error"
        assert result.error == "StorageError"

    def test_unexpected_exception_returns_failure(
        self,
        mock_extractor: MagicMock,
        mock_renderer: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """Unknown exceptions are captured and reported as failure."""
        mock_extractor.extract.side_effect = RuntimeError("boom")
        use_case = ConvertPdfUseCase(
            mock_extractor, mock_renderer, mock_storage
        )
        result = use_case.execute(
            ConvertPdfRequest(pdf_path=Path("x"), output_dir=Path("/o"))
        )
        assert result.status == "error"
        assert result.error == "RuntimeError"
        assert "boom" in result.error_message


class TestConvertPdfUseCaseResultShape:
    """The :class:`ConvertPdfResult` shape is stable across success/failure."""

    def test_result_has_required_fields(self) -> None:
        """Result has every documented attribute (spec §5.6)."""
        result = ConvertPdfResult(
            status="success",
            output_path=Path("/x.md"),
            image_count=1,
            table_count=2,
            page_count=3,
            elapsed_seconds=0.5,
        )
        assert result.status == "success"
        assert result.output_path == Path("/x.md")
        assert result.image_count == 1
        assert result.table_count == 2
        assert result.page_count == 3
        assert result.elapsed_seconds == 0.5
        assert result.error is None
        assert result.error_message == ""


@pytest.fixture
def mock_extractor() -> MagicMock:
    extractor = MagicMock(spec=IExtractor)
    return extractor


@pytest.fixture
def mock_renderer() -> MagicMock:
    return MagicMock(spec=IRenderer)


@pytest.fixture
def mock_storage() -> MagicMock:
    return MagicMock(spec=IStorage)

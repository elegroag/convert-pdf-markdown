"""Tests for the use cases (ConvertPdfUseCase, BatchConvertUseCase).

The use cases are pure domain: they only know about the ports they
depend on. These tests use mocks for the ports and verify the
orchestration logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from pdf2md.domain.entities.entities import (
    MarkdownDocument,
    MarkdownPage,
    PdfDocument,
    PdfMetadata,
    PdfPage,
)
from pdf2md.domain.exceptions import (
    CorruptedPdfError,
    EncryptedPdfError,
    ExtractionError,
)
from pdf2md.domain.ports.ports import IBatchRunner, IExtractor, IRenderer, IStorage
from pdf2md.domain.use_cases.use_cases import (
    BatchConvertUseCase,
    BatchConfig,
    ConvertPdfRequest,
    ConvertPdfUseCase,
)
from pdf2md.domain.value_objects.value_objects import ConversionConfig


class _FakeExtractor(IExtractor):
    def __init__(self, doc: PdfDocument | None = None, error: Exception | None = None) -> None:
        self._doc = doc or PdfDocument(
            file_path=Path("x.pdf"),
            page_count=2,
            metadata=PdfMetadata(title="T"),
            pages=[
                PdfPage(page_number=1),
                PdfPage(
                    page_number=2,
                    images=[_img()],
                    tables=[_table()],
                ),
            ],
        )
        self._error = error
        self.calls: list[Path] = []

    def extract(self, pdf_path: Path) -> PdfDocument:
        self.calls.append(pdf_path)
        if self._error is not None:
            raise self._error
        return self._doc


class _FakeRenderer(IRenderer):
    def __init__(self, doc: MarkdownDocument | None = None) -> None:
        self._doc = doc or MarkdownDocument(
            source_pdf=Path("x.pdf"),
            pages=[MarkdownPage(page_number=1, content="# Title")],
        )
        self.calls: list[PdfDocument] = []

    def render(self, document: PdfDocument) -> MarkdownDocument:
        self.calls.append(document)
        return self._doc


class _FakeStorage(IStorage):
    def __init__(self, path: Path | None = None, error: Exception | None = None) -> None:
        self._path = path or Path("/tmp/out/x.md")
        self._error = error
        self.calls: list[MarkdownDocument] = []

    def save(self, document: MarkdownDocument, source: PdfDocument | None = None) -> Path:
        self.calls.append(document)
        if self._error is not None:
            raise self._error
        return self._path


class _SequentialRunner(IBatchRunner):
    def __init__(self) -> None:
        self.workers_used: int | None = None

    def run(self, items: list, worker, *, workers: int) -> list:
        self.workers_used = workers
        return [worker(item) for item in items]


def _img() -> Any:
    from pdf2md.domain.entities.entities import ImageAsset

    return ImageAsset(
        image_id="p2_img1",
        page_number=2,
        bbox=(0, 0, 10, 10),
        format="PNG",
        raw_bytes=b"\x89PNG",
    )


def _table() -> Any:
    from pdf2md.domain.entities.entities import TableNode

    return TableNode(page_number=2, bbox=(0, 0, 10, 10))


class TestConvertPdfUseCaseSuccessPath:
    """Happy-path orchestration: extractor → renderer → storage."""

    def test_returns_success_with_metrics(self) -> None:
        extractor = _FakeExtractor()
        renderer = _FakeRenderer()
        storage = _FakeStorage()
        use_case = ConvertPdfUseCase(extractor, renderer, storage)

        result = use_case.execute(
            ConvertPdfRequest(
                pdf_path=Path("x.pdf"),
                output_dir=Path("/tmp/out"),
            )
        )

        assert result.status == "success"
        assert result.output_path == Path("/tmp/out/x.md")
        assert result.image_count == 1
        assert result.table_count == 1
        assert result.page_count == 2
        assert result.error is None
        assert extractor.calls == [Path("x.pdf")]
        assert len(renderer.calls) == 1
        assert len(storage.calls) == 1

    def test_zero_images_and_tables_reported_correctly(self) -> None:
        doc = PdfDocument(file_path=Path("x.pdf"), page_count=1, pages=[PdfPage(1)])
        result = ConvertPdfUseCase(
            _FakeExtractor(doc), _FakeRenderer(), _FakeStorage()
        ).execute(
            ConvertPdfRequest(pdf_path=Path("x.pdf"), output_dir=Path("/tmp/out"))
        )
        assert result.image_count == 0
        assert result.table_count == 0
        assert result.page_count == 1


class TestConvertPdfUseCaseErrorPath:
    """Errors are translated to a result with ``status='error'``."""

    @pytest.mark.parametrize(
        "exc",
        [EncryptedPdfError("locked"), CorruptedPdfError("bad"), ExtractionError("oops")],
    )
    def test_extraction_errors_become_error_result(self, exc: Exception) -> None:
        use_case = ConvertPdfUseCase(
            _FakeExtractor(error=exc), _FakeRenderer(), _FakeStorage()
        )
        result = use_case.execute(
            ConvertPdfRequest(pdf_path=Path("x.pdf"), output_dir=Path("/tmp/out"))
        )
        assert result.status == "error"
        assert result.error == type(exc).__name__
        assert result.error_message == str(exc)
        assert result.output_path is None

    def test_storage_error_becomes_error_result(self) -> None:
        err = RuntimeError("disk full")
        use_case = ConvertPdfUseCase(
            _FakeExtractor(),
            _FakeRenderer(),
            _FakeStorage(error=err),
        )
        result = use_case.execute(
            ConvertPdfRequest(pdf_path=Path("x.pdf"), output_dir=Path("/tmp/out"))
        )
        assert result.status == "error"
        assert result.error == "RuntimeError"

    def test_elapsed_seconds_is_positive(self) -> None:
        result = ConvertPdfUseCase(
            _FakeExtractor(), _FakeRenderer(), _FakeStorage()
        ).execute(
            ConvertPdfRequest(pdf_path=Path("x.pdf"), output_dir=Path("/tmp/out"))
        )
        assert result.elapsed_seconds >= 0


class TestBatchConvertUseCase:
    """BatchConvertUseCase fans out PDFs to the convert use case."""

    def test_empty_directory_returns_empty_report(self, tmp_path: Path) -> None:
        runner = _SequentialRunner()
        use_case = BatchConvertUseCase(runner, _fake_convert())
        report = use_case.execute(tmp_path, BatchConfig())
        assert report.total == 0
        assert report.success == 0
        assert report.failed == 0
        assert report.results == []

    def test_collects_per_file_results(self, tmp_path: Path) -> None:
        (tmp_path / "a.pdf").write_bytes(b"")
        (tmp_path / "b.pdf").write_bytes(b"")
        runner = _SequentialRunner()
        use_case = BatchConvertUseCase(runner, _fake_convert())
        report = use_case.execute(tmp_path, BatchConfig())
        assert report.total == 2
        assert report.success == 2
        assert report.failed == 0
        assert {r.file for r in report.results} == {"a.pdf", "b.pdf"}

    def test_reports_failures_with_error_name(self, tmp_path: Path) -> None:
        (tmp_path / "broken.pdf").write_bytes(b"")
        runner = _SequentialRunner()
        use_case = BatchConvertUseCase(
            runner,
            _fake_convert(error=CorruptedPdfError("eof")),
        )
        report = use_case.execute(tmp_path, BatchConfig())
        assert report.total == 1
        assert report.success == 0
        assert report.failed == 1
        assert report.results[0].error == "CorruptedPdfError"

    def test_report_to_json_is_serializable(self, tmp_path: Path) -> None:
        (tmp_path / "a.pdf").write_bytes(b"")
        runner = _SequentialRunner()
        use_case = BatchConvertUseCase(runner, _fake_convert())
        report = use_case.execute(tmp_path, BatchConfig())
        import json

        json.loads(report.to_json())

    def test_workers_count_is_passed_to_runner(self, tmp_path: Path) -> None:
        (tmp_path / "a.pdf").write_bytes(b"")
        runner = _SequentialRunner()
        use_case = BatchConvertUseCase(runner, _fake_convert())
        use_case.execute(tmp_path, BatchConfig(workers=4))
        assert runner.workers_used == 4


def _fake_convert(error: Exception | None = None) -> ConvertPdfUseCase:
    if error is not None:
        extractor = _FakeExtractor(error=error)
    else:
        extractor = _FakeExtractor()
    return ConvertPdfUseCase(extractor, _FakeRenderer(), _FakeStorage())

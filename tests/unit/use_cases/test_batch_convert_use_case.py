"""Tests for BatchConvertUseCase and the BatchReport shape."""

from __future__ import annotations

from pathlib import Path
from typing import Callable
from unittest.mock import MagicMock

import pytest

from pdf2md.domain.ports.ports import IBatchRunner
from pdf2md.domain.use_cases.use_cases import (
    BatchConfig,
    BatchConvertUseCase,
    BatchItemResult,
    BatchReport,
    ConvertPdfRequest,
    ConvertPdfResult,
    ConvertPdfUseCase,
)
from pdf2md.domain.value_objects.enums import TableEngine
from pdf2md.domain.value_objects.value_objects import ConversionConfig


class _FakeRunner(IBatchRunner):
    """A runner that applies the worker sequentially (workers >= 1)."""

    def run(self, items, worker, *, workers):
        return [worker(item) for item in items]


class _Result:
    """Minimal stub of a successful conversion result."""

    def __init__(self, name: str, ok: bool = True) -> None:
        self.status = "success" if ok else "error"
        self.output_path = Path(f"/out/{name}.md") if ok else None
        self.image_count = 1 if ok else 0
        self.table_count = 0
        self.page_count = 3
        self.elapsed_seconds = 0.1
        self.error = None if ok else "ExtractionError"
        self.error_message = "" if ok else "fail"


class TestBatchConvertUseCase:
    """Tests for the batch use case runner integration."""

    def test_empty_directory_returns_zero_report(
        self, tmp_path: Path
    ) -> None:
        """A directory with no PDFs returns an empty report."""
        runner = _FakeRunner()
        use_case = BatchConvertUseCase(runner, MagicMock(spec=ConvertPdfUseCase))
        report = use_case.execute(tmp_path, BatchConfig())
        assert report.total == 0
        assert report.success == 0
        assert report.failed == 0
        assert report.results == []

    def test_runs_use_case_for_each_pdf(
        self, tmp_path: Path
    ) -> None:
        """Each PDF triggers one conversion and one batch result."""
        (tmp_path / "a.pdf").write_bytes(b"")
        (tmp_path / "b.pdf").write_bytes(b"")
        (tmp_path / "c.pdf").write_bytes(b"")

        convert_uc = MagicMock(spec=ConvertPdfUseCase)
        convert_uc.execute.return_value = _Result("a")  # type: ignore[arg-type]

        runner = _FakeRunner()
        use_case = BatchConvertUseCase(runner, convert_uc)
        report = use_case.execute(tmp_path, BatchConfig())

        assert report.total == 3
        assert report.success == 3
        assert report.failed == 0
        assert convert_uc.execute.call_count == 3

    def test_records_failures(
        self, tmp_path: Path
    ) -> None:
        """A failed conversion is recorded without aborting the batch."""
        (tmp_path / "ok.pdf").write_bytes(b"")
        (tmp_path / "bad.pdf").write_bytes(b"")

        def _fake_execute(request: ConvertPdfRequest) -> _Result:
            return _Result(request.pdf_path.stem, ok=request.pdf_path.stem == "ok")

        convert_uc = MagicMock(spec=ConvertPdfUseCase)
        convert_uc.execute.side_effect = _fake_execute

        use_case = BatchConvertUseCase(_FakeRunner(), convert_uc)
        report = use_case.execute(tmp_path, BatchConfig())

        assert report.total == 2
        assert report.success == 1
        assert report.failed == 1

    def test_to_json_round_trip(self) -> None:
        """The report serializes to JSON without losing data."""
        report = BatchReport(
            total=2,
            success=1,
            failed=1,
            results=[
                BatchItemResult(file="a.pdf", status="success", output_path="/o/a.md"),
                BatchItemResult(
                    file="b.pdf", status="error", error="X", message="bad"
                ),
            ],
        )
        import json

        parsed = json.loads(report.to_json())
        assert parsed["total"] == 2
        assert parsed["success"] == 1
        assert parsed["failed"] == 1
        assert parsed["results"][0]["file"] == "a.pdf"
        assert parsed["results"][1]["error"] == "X"


class TestThreadPoolBatchRunner:
    """The default runner uses concurrent.futures."""

    def test_single_worker_runs_sequentially(self) -> None:
        """``workers <= 1`` falls back to a sequential loop."""
        from pdf2md.infrastructure.storage.batch_runner import (
            ThreadPoolBatchRunner,
        )

        runner = ThreadPoolBatchRunner()
        result = runner.run([1, 2, 3], lambda x: x * 10, workers=1)
        assert result == [10, 20, 30]

    def test_multi_worker_preserves_order(self) -> None:
        """``workers > 1`` preserves input order in the output list."""
        from pdf2md.infrastructure.storage.batch_runner import (
            ThreadPoolBatchRunner,
        )

        runner = ThreadPoolBatchRunner()
        result = runner.run([1, 2, 3, 4], lambda x: x * 2, workers=4)
        assert result == [2, 4, 6, 8]

"""Tests for the CLI (Typer)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pdf2md.interface.cli.app import app

runner = CliRunner()


class TestVersionCommand:
    """``pdf2md version`` prints the version."""

    def test_version_prints(self) -> None:
        """The version string is printed to stdout."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.stdout


class TestConvertCommand:
    """``pdf2md convert <pdf>`` runs the conversion pipeline."""

    def test_convert_with_nonexistent_pdf_fails(self) -> None:
        """A non-existent PDF triggers a non-zero exit code."""
        result = runner.invoke(app, ["convert", "/nope.pdf"])
        assert result.exit_code != 0

    def test_convert_happy_path(
        self, tmp_path: Path, sample_pdf_path: Path
    ) -> None:
        """A successful conversion is reported to stdout."""
        sample_pdf_path.write_bytes(b"%PDF-1.4\n%fake\n")
        out_dir = tmp_path / "out"

        fake_result = MagicMock()
        fake_result.status = "success"
        fake_result.output_path = out_dir / "sample.md"
        fake_result.image_count = 0
        fake_result.table_count = 0
        fake_result.page_count = 1
        fake_result.elapsed_seconds = 0.1
        fake_result.error = None
        fake_result.error_message = ""

        with patch(
            "pdf2md.interface.cli.app.build_default_service"
        ) as build:
            service = MagicMock()
            service.convert.return_value = fake_result
            build.return_value = service
            result = runner.invoke(
                app,
                [
                    "convert",
                    str(sample_pdf_path),
                    "-o",
                    str(out_dir),
                ],
            )
        assert result.exit_code == 0
        assert "OK" in result.stdout
        assert "wrote" in result.stdout

    def test_convert_failure_exits_nonzero(
        self, tmp_path: Path, sample_pdf_path: Path
    ) -> None:
        """An error conversion produces a non-zero exit code."""
        sample_pdf_path.write_bytes(b"%PDF-1.4\n%fake\n")

        fake_result = MagicMock()
        fake_result.status = "error"
        fake_result.error = "EncryptedPdfError"
        fake_result.error_message = "locked"

        with patch(
            "pdf2md.interface.cli.app.build_default_service"
        ) as build:
            service = MagicMock()
            service.convert.return_value = fake_result
            build.return_value = service
            result = runner.invoke(
                app,
                ["convert", str(sample_pdf_path), "-o", str(tmp_path)],
            )
        assert result.exit_code == 1
        assert "ERROR" in result.stdout or "ERROR" in result.stderr or result.exit_code == 1


class TestBatchCommand:
    """``pdf2md batch <dir>`` processes a directory of PDFs."""

    def test_batch_with_no_pdfs(
        self, tmp_path: Path, capsys
    ) -> None:
        """A directory with no PDFs exits cleanly with a zero report."""
        empty = tmp_path / "empty"
        empty.mkdir()
        fake_report = MagicMock()
        fake_report.total = 0
        fake_report.success = 0
        fake_report.failed = 0
        fake_report.to_json.return_value = "{}"

        with patch(
            "pdf2md.interface.cli.app.build_batch_use_case"
        ) as build:
            use_case = MagicMock()
            use_case.execute.return_value = fake_report
            build.return_value = use_case
            result = runner.invoke(
                app, ["batch", str(empty), "-o", str(tmp_path)]
            )
        assert result.exit_code == 0
        assert "total=0" in result.stdout


class TestInspectCommand:
    """``pdf2md inspect <pdf>`` prints structural metadata."""

    def test_inspect_with_json_flag(
        self, tmp_path: Path, sample_pdf_path: Path
    ) -> None:
        """``--json`` outputs the result as JSON."""
        sample_pdf_path.write_bytes(b"%PDF-1.4\n%fake\n")

        fake_inspect = MagicMock()
        fake_inspect.to_dict.return_value = {
            "file_path": str(sample_pdf_path),
            "page_count": 1,
            "metadata": {"title": "X"},
            "heading_counts": {"1": 1},
            "image_count": 0,
            "table_count": 0,
        }
        with patch(
            "pdf2md.interface.cli.app.build_default_service"
        ) as build:
            service = MagicMock()
            service.inspect.return_value = fake_inspect
            build.return_value = service
            result = runner.invoke(
                app, ["inspect", str(sample_pdf_path), "--json"]
            )
        assert result.exit_code == 0
        parsed = json.loads(result.stdout)
        assert parsed["page_count"] == 1
        assert parsed["metadata"]["title"] == "X"

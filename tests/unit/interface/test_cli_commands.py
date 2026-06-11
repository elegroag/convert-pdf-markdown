"""Tests for the CLI commands that don't require a real PDF.

These tests exercise the Typer wiring and argument parsing without
hitting the filesystem or PDF parsers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pdf2md.interface.cli.app import app

runner = CliRunner()


@pytest.fixture
def existing_pdf(tmp_path: Path) -> Path:
    """An empty file that exists and is readable — passes Typer's validation."""
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%fake\n")
    return pdf


class TestCliVersion:
    def test_version_command_prints_version(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "pdf2md" in result.stdout


class TestCliSubcommandHelp:
    def test_convert_help(self) -> None:
        result = runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.stdout
        assert "--extractor" in result.stdout

    def test_batch_help(self) -> None:
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "--workers" in result.stdout

    def test_inspect_help(self) -> None:
        result = runner.invoke(app, ["inspect", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.stdout


class TestCliConvertInvokesService:
    """``convert`` delegates to ``ConversionService`` and exits 0 on success."""

    def test_convert_calls_service_and_exits_zero(
        self, tmp_path: Path, existing_pdf: Path
    ) -> None:
        fake_result = MagicMock()
        fake_result.status = "success"
        fake_result.output_path = tmp_path / "out.md"
        fake_result.image_count = 0
        fake_result.table_count = 0
        fake_result.page_count = 1
        fake_result.elapsed_seconds = 0.01
        fake_result.error = None
        fake_result.error_message = ""

        with patch("pdf2md.interface.cli.app.build_default_service") as build:
            service = MagicMock()
            service.convert.return_value = fake_result
            build.return_value = service

            result = runner.invoke(
                app,
                [
                    "convert",
                    str(existing_pdf),
                    "--output",
                    str(tmp_path),
                ],
            )
        assert result.exit_code == 0

    def test_convert_failure_exits_nonzero(self, tmp_path: Path, existing_pdf: Path) -> None:
        fake_result = MagicMock()
        fake_result.status = "error"
        fake_result.error = "CorruptedPdfError"
        fake_result.error_message = "oops"

        with patch("pdf2md.interface.cli.app.build_default_service") as build:
            service = MagicMock()
            service.convert.return_value = fake_result
            build.return_value = service

            result = runner.invoke(
                app,
                [
                    "convert",
                    str(existing_pdf),
                    "--output",
                    str(tmp_path),
                ],
            )
        assert result.exit_code != 0


class TestCliInspectInvokesService:
    def test_inspect_pretty(self, existing_pdf: Path) -> None:
        fake_result = MagicMock()
        fake_result.metadata = {"title": "T"}
        fake_result.page_count = 1
        fake_result.image_count = 0
        fake_result.table_count = 0
        fake_result.heading_counts = {1: 2}

        with patch("pdf2md.interface.cli.app.build_default_service") as build:
            service = MagicMock()
            service.inspect.return_value = fake_result
            build.return_value = service

            result = runner.invoke(app, ["inspect", str(existing_pdf)])
        assert result.exit_code == 0

    def test_inspect_json(self, existing_pdf: Path) -> None:
        fake_result = MagicMock()
        fake_result.metadata = {"title": "T"}
        fake_result.page_count = 1
        fake_result.image_count = 0
        fake_result.table_count = 0
        fake_result.heading_counts = {1: 2}
        fake_result.to_dict.return_value = {"page_count": 1}

        with patch("pdf2md.interface.cli.app.build_default_service") as build:
            service = MagicMock()
            service.inspect.return_value = fake_result
            build.return_value = service

            result = runner.invoke(
                app, ["inspect", str(existing_pdf), "--json"]
            )
        assert result.exit_code == 0
        json.loads(result.stdout)

"""Tests for xlsx2md CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from xlsx2md.interface.cli.app import app

runner = CliRunner()


@pytest.fixture
def existing_xlsx(tmp_path: Path) -> Path:
    xlsx = tmp_path / "sample.xlsx"
    xlsx.write_bytes(b"PK\x03\x04")
    return xlsx


class TestCliVersion:
    def test_version_command_prints_version(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "xlsx2md" in result.stdout


class TestCliSubcommandHelp:
    def test_convert_help(self) -> None:
        result = runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.stdout

    def test_batch_help(self) -> None:
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "--workers" in result.stdout


class TestCliConvertInvokesService:
    def test_convert_calls_service_and_exits_zero(
        self, tmp_path: Path, existing_xlsx: Path
    ) -> None:
        fake_result = MagicMock()
        fake_result.status = "success"
        fake_result.sheet_outputs = (tmp_path / "book" / "resumen.md",)
        fake_result.index_path = tmp_path / "book" / "_index.md"
        fake_result.total_sheets = 1
        fake_result.total_rows = 4
        fake_result.total_images = 0
        fake_result.elapsed_seconds = 0.01
        fake_result.error = None
        fake_result.error_message = ""

        with patch("xlsx2md.interface.cli.app.build_default_service") as build:
            service = MagicMock()
            service.convert.return_value = fake_result
            build.return_value = service

            result = runner.invoke(
                app,
                ["convert", str(existing_xlsx), "--output", str(tmp_path)],
            )
        assert result.exit_code == 0

    def test_convert_failure_exits_nonzero(self, tmp_path: Path, existing_xlsx: Path) -> None:
        fake_result = MagicMock()
        fake_result.status = "error"
        fake_result.error = "CorruptedXlsxError"
        fake_result.error_message = "oops"

        with patch("xlsx2md.interface.cli.app.build_default_service") as build:
            service = MagicMock()
            service.convert.return_value = fake_result
            build.return_value = service

            result = runner.invoke(
                app,
                ["convert", str(existing_xlsx), "--output", str(tmp_path)],
            )
        assert result.exit_code != 0

    def test_rejects_non_xlsx_extension(self, tmp_path: Path) -> None:
        txt = tmp_path / "file.txt"
        txt.write_text("hello")
        result = runner.invoke(app, ["convert", str(txt), "--output", str(tmp_path)])
        assert result.exit_code != 0

"""Tests for md2docx CLI commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from md2docx.interface.cli.app import app

runner = CliRunner()


@pytest.fixture
def existing_md(tmp_path: Path) -> Path:
    md = tmp_path / "sample.md"
    md.write_text("# Sample\n\nBody", encoding="utf-8")
    return md


class TestCliVersion:
    def test_version_command_prints_version(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "md2docx" in result.stdout


class TestCliSubcommandHelp:
    def test_convert_help(self) -> None:
        result = runner.invoke(app, ["convert", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.stdout
        assert "--source-dir" in result.stdout

    def test_batch_help(self) -> None:
        result = runner.invoke(app, ["batch", "--help"])
        assert result.exit_code == 0
        assert "--workers" in result.stdout


class TestCliConvertInvokesService:
    def test_convert_calls_service_and_exits_zero(
        self, tmp_path: Path, existing_md: Path
    ) -> None:
        fake_result = MagicMock()
        fake_result.status = "success"
        fake_result.docx_path = tmp_path / "out.docx"
        fake_result.md_path = tmp_path / "out.md"
        fake_result.sections = 1
        fake_result.refined = True
        fake_result.elapsed_seconds = 0.01
        fake_result.error = None
        fake_result.error_message = ""

        with patch("md2docx.interface.cli.app.build_default_service") as build:
            service = MagicMock()
            service.convert.return_value = fake_result
            build.return_value = service

            result = runner.invoke(
                app,
                ["convert", str(existing_md), "--output", str(tmp_path)],
            )
        assert result.exit_code == 0

    def test_convert_failure_exits_nonzero(self, tmp_path: Path, existing_md: Path) -> None:
        fake_result = MagicMock()
        fake_result.status = "error"
        fake_result.error = "PandocNotFoundError"
        fake_result.error_message = "missing"

        with patch("md2docx.interface.cli.app.build_default_service") as build:
            service = MagicMock()
            service.convert.return_value = fake_result
            build.return_value = service

            result = runner.invoke(
                app,
                ["convert", str(existing_md), "--output", str(tmp_path)],
            )
        assert result.exit_code != 0

    def test_rejects_non_md_extension(self, tmp_path: Path) -> None:
        txt = tmp_path / "file.txt"
        txt.write_text("hello")
        result = runner.invoke(app, ["convert", str(txt), "--output", str(tmp_path)])
        assert result.exit_code != 0

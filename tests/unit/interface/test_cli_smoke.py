"""Smoke tests for the CLI application."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from pdf2md.interface.cli.app import app


runner = CliRunner()


class TestCliVersion:
    """``pdf2md version`` prints the library version."""

    def test_version_exits_zero(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "pdf2md" in result.stdout


class TestCliHelp:
    """``pdf2md --help`` lists subcommands."""

    def test_help_lists_convert(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "convert" in result.stdout

    def test_help_lists_batch(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "batch" in result.stdout

    def test_help_lists_inspect(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "inspect" in result.stdout

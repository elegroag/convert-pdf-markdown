"""Tests for the pdf2md MCP server."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pdf2md.application.dto.dtos import ConversionResult
from pdf2md.interface.mcp.server import (
    format_conversion_result,
    resolve_output_paths,
    run_conversion,
)


class TestResolveOutputPaths:
    def test_directory_destination(self) -> None:
        pdf = Path("/tmp/book.pdf")
        out_dir, expected = resolve_output_paths(pdf, Path("/tmp/output"))
        assert out_dir == Path("/tmp/output")
        assert expected == Path("/tmp/output/book.md")

    def test_file_destination(self) -> None:
        pdf = Path("/tmp/book.pdf")
        out_dir, expected = resolve_output_paths(
            pdf, Path("/tmp/output/custom.md")
        )
        assert out_dir == Path("/tmp/output")
        assert expected == Path("/tmp/output/custom.md")


class TestFormatConversionResult:
    def test_success_payload(self) -> None:
        result = ConversionResult(
            status="success",
            output_path=Path("/out/book.md"),
            page_count=10,
            image_count=2,
            table_count=1,
            elapsed_seconds=1.234,
        )
        payload = json.loads(format_conversion_result(result))
        assert payload["status"] == "success"
        assert payload["output_path"] == "/out/book.md"
        assert payload["page_count"] == 10


class TestRunConversion:
    def test_missing_pdf_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="PDF not found"):
            run_conversion(tmp_path / "missing.pdf", tmp_path / "out")

    def test_renames_output_when_custom_md_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pdf = tmp_path / "sample.pdf"
        pdf.write_bytes(b"%PDF-1.4\n")

        default_md = tmp_path / "out" / "sample.md"
        custom_md = tmp_path / "out" / "custom.md"

        mock_service = MagicMock()
        mock_service.convert.return_value = ConversionResult(
            status="success",
            output_path=default_md,
            page_count=1,
        )
        mock_factory = MagicMock(return_value=mock_service)
        mock_loader = MagicMock(return_value=MagicMock())

        default_md.parent.mkdir(parents=True)
        default_md.write_text("# default", encoding="utf-8")

        result = run_conversion(
            pdf,
            custom_md,
            service_factory=mock_factory,
            config_loader=mock_loader,
        )

        assert result.output_path == custom_md.resolve()
        assert custom_md.read_text(encoding="utf-8") == "# default"
        assert not default_md.exists()

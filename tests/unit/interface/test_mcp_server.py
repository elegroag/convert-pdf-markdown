"""Tests for the convert2md MCP server."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from docx2md.application.dto.dtos import ConversionResult as DocxConversionResult
from md2docx.application.dto.dtos import ConversionResult as Md2DocxConversionResult
from pdf2md.application.dto.dtos import ConversionResult
from pdf2md.interface.mcp.server import (
    format_conversion_result,
    format_docx_conversion_result,
    format_md2docx_conversion_result,
    format_xlsx_conversion_result,
    resolve_md2docx_output_paths,
    resolve_output_paths,
    run_conversion,
    run_docx_conversion,
    run_md2docx_conversion,
    run_xlsx_conversion,
)
from xlsx2md.application.dto.dtos import ConversionResult as XlsxConversionResult


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


class TestRunDocxConversion:
    def test_missing_docx_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="DOCX not found"):
            run_docx_conversion(tmp_path / "missing.docx", tmp_path / "out")

    def test_non_docx_extension_raises(self, tmp_path: Path) -> None:
        txt = tmp_path / "file.txt"
        txt.write_text("hello")
        with pytest.raises(ValueError, match="\\.docx extension"):
            run_docx_conversion(txt, tmp_path / "out")

    def test_renames_output_when_custom_md_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        docx = tmp_path / "sample.docx"
        docx.write_bytes(b"PK\x03\x04")

        default_md = tmp_path / "out" / "sample.md"
        custom_md = tmp_path / "out" / "custom.md"

        mock_service = MagicMock()
        mock_service.convert.return_value = DocxConversionResult(
            status="success",
            output_path=default_md,
            total_blocks=3,
            headings=1,
        )
        mock_factory = MagicMock(return_value=mock_service)

        default_md.parent.mkdir(parents=True)
        default_md.write_text("# default", encoding="utf-8")

        result = run_docx_conversion(
            docx,
            custom_md,
            service_factory=mock_factory,
        )

        assert result.output_path == custom_md.resolve()
        assert custom_md.read_text(encoding="utf-8") == "# default"
        assert not default_md.exists()


class TestFormatDocxConversionResult:
    def test_success_payload(self) -> None:
        result = DocxConversionResult(
            status="success",
            output_path=Path("/out/report.md"),
            total_blocks=10,
            headings=3,
            images=2,
            tables=1,
            elapsed_seconds=0.5,
        )
        payload = json.loads(format_docx_conversion_result(result))
        assert payload["status"] == "success"
        assert payload["output_path"] == "/out/report.md"
        assert payload["headings"] == 3


class TestRunXlsxConversion:
    def test_missing_xlsx_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="XLSX not found"):
            run_xlsx_conversion(tmp_path / "missing.xlsx", tmp_path / "out")

    def test_non_xlsx_extension_raises(self, tmp_path: Path) -> None:
        txt = tmp_path / "file.txt"
        txt.write_text("hello")
        with pytest.raises(ValueError, match="\\.xlsx extension"):
            run_xlsx_conversion(txt, tmp_path / "out")

    def test_happy_path_with_mocked_service(self, tmp_path: Path) -> None:
        xlsx = tmp_path / "sample.xlsx"
        xlsx.write_bytes(b"PK\x03\x04")
        out_dir = tmp_path / "out"
        sheet_a = out_dir / "sample" / "sheet-a.md"
        sheet_b = out_dir / "sample" / "sheet-b.md"
        index_path = out_dir / "sample" / "_index.md"

        mock_service = MagicMock()
        mock_service.convert.return_value = XlsxConversionResult(
            status="success",
            sheet_outputs=(sheet_a, sheet_b),
            index_path=index_path,
            total_sheets=2,
            total_rows=10,
            total_images=1,
            elapsed_seconds=0.42,
        )
        mock_factory = MagicMock(return_value=mock_service)

        result = run_xlsx_conversion(
            xlsx,
            out_dir,
            service_factory=mock_factory,
        )

        assert result.status == "success"
        assert len(result.sheet_outputs) == 2
        assert result.index_path == index_path
        mock_factory.assert_called_once()
        mock_service.convert.assert_called_once()


class TestFormatXlsxConversionResult:
    def test_success_payload(self) -> None:
        result = XlsxConversionResult(
            status="success",
            sheet_outputs=(Path("/out/book/sheet-a.md"), Path("/out/book/sheet-b.md")),
            index_path=Path("/out/book/_index.md"),
            total_sheets=2,
            total_rows=25,
            total_images=3,
            elapsed_seconds=0.876,
        )
        payload = json.loads(format_xlsx_conversion_result(result))
        assert payload["status"] == "success"
        assert payload["sheet_outputs"] == [
            "/out/book/sheet-a.md",
            "/out/book/sheet-b.md",
        ]
        assert payload["index_path"] == "/out/book/_index.md"
        assert payload["total_sheets"] == 2
        assert payload["elapsed_seconds"] == 0.88


class TestResolveMd2DocxOutputPaths:
    def test_directory_destination(self) -> None:
        md = Path("/tmp/manual.md")
        out_dir, expected = resolve_md2docx_output_paths(md, Path("/tmp/output"))
        assert out_dir == Path("/tmp/output")
        assert expected == Path("/tmp/output/manual.docx")

    def test_file_destination(self) -> None:
        md = Path("/tmp/manual.md")
        out_dir, expected = resolve_md2docx_output_paths(
            md, Path("/tmp/output/custom.docx")
        )
        assert out_dir == Path("/tmp/output")
        assert expected == Path("/tmp/output/custom.docx")


class TestFormatMd2DocxConversionResult:
    def test_success_payload(self) -> None:
        result = Md2DocxConversionResult(
            status="success",
            docx_path=Path("/out/manual.docx"),
            md_path=Path("/out/manual.md"),
            sections=3,
            refined=True,
            elapsed_seconds=1.234,
        )
        payload = json.loads(format_md2docx_conversion_result(result))
        assert payload["status"] == "success"
        assert payload["docx_path"] == "/out/manual.docx"
        assert payload["refined"] is True


class TestRunMd2DocxConversion:
    def test_missing_md_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Markdown not found"):
            run_md2docx_conversion(tmp_path / "missing.md", tmp_path / "out")

    def test_non_md_extension_raises(self, tmp_path: Path) -> None:
        txt = tmp_path / "file.txt"
        txt.write_text("hello")
        with pytest.raises(ValueError, match="\\.md extension"):
            run_md2docx_conversion(txt, tmp_path / "out")

    def test_happy_path_with_mocked_service(self, tmp_path: Path) -> None:
        md = tmp_path / "sample.md"
        md.write_text("# Sample", encoding="utf-8")
        out_dir = tmp_path / "out"
        docx_path = out_dir / "sample.docx"

        mock_service = MagicMock()
        mock_service.convert.return_value = Md2DocxConversionResult(
            status="success",
            docx_path=docx_path,
            md_path=out_dir / "MANUAL_COMPLETO.md",
            sections=1,
            refined=False,
            elapsed_seconds=0.5,
        )
        mock_factory = MagicMock(return_value=mock_service)

        result = run_md2docx_conversion(
            md,
            out_dir,
            service_factory=mock_factory,
        )
        assert result.status == "success"
        mock_factory.assert_called_once()
        mock_service.convert.assert_called_once()

    def test_pandoc_error_propagates_via_result(self, tmp_path: Path) -> None:
        md = tmp_path / "sample.md"
        md.write_text("# Sample", encoding="utf-8")

        mock_service = MagicMock()
        mock_service.convert.return_value = Md2DocxConversionResult(
            status="error",
            error="PandocNotFoundError",
            error_message="missing",
        )
        mock_factory = MagicMock(return_value=mock_service)

        result = run_md2docx_conversion(
            md,
            tmp_path / "out",
            service_factory=mock_factory,
        )
        assert result.status == "error"
        assert result.error == "PandocNotFoundError"


class TestMcpServerMetadata:
    def test_server_name_is_generic(self) -> None:
        from pdf2md.interface.mcp.server import mcp

        assert mcp.name == "convert2md"

    def test_exposes_four_tools(self) -> None:
        import asyncio

        from pdf2md.interface.mcp.server import mcp

        tools = asyncio.run(mcp.list_tools())
        tool_names = {tool.name for tool in tools}
        assert tool_names == {
            "convert_pdf_to_markdown",
            "convert_docx_to_markdown",
            "convert_xlsx_to_markdown",
            "convert_markdown_to_docx",
        }

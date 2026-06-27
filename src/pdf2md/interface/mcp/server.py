"""MCP server exposing PDF and Word → Markdown conversion.

Run with uvx (stdio transport, no authentication)::

    uvx --from "./[mcp]" pdf2md-mcp

Or with an absolute path::

    uvx --from "/path/to/convert-pdf-markdown[mcp]" pdf2md-mcp

Cursor / Claude Desktop example (``mcp.json``)::

    {
      "mcpServers": {
        "pdf2md": {
          "command": "uvx",
          "args": [
            "--from", "/path/to/convert-pdf-markdown[mcp]",
            "pdf2md-mcp"
          ]
        }
      }
    }
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

from fastmcp import FastMCP

from docx2md.application.dto.dtos import ConversionRequest as DocxConversionRequest
from docx2md.application.dto.dtos import ConversionResult as DocxConversionResult
from docx2md.application.services.conversion_service import (
    ConversionService as DocxConversionService,
)
from docx2md.config.service_factory import build_default_service as build_docx_service
from docx2md.domain.services.anchor_slug import AnchorSlug as DocxAnchorSlug
from docx2md.domain.value_objects.value_objects import ConversionConfig as DocxConversionConfig
from pdf2md.application.dto.dtos import ConversionRequest, ConversionResult
from pdf2md.application.services.conversion_service import ConversionService
from pdf2md.config.config_loader import load_config
from pdf2md.config.service_factory import build_default_service
from pdf2md.domain.services.anchor_slug import AnchorSlug

mcp = FastMCP(
    name="pdf2md",
    instructions=(
        "Convert PDF and Word (.docx) documents to structured Markdown with "
        "headings, images, tables, links, and code blocks."
    ),
)


def resolve_output_paths(
    source_path: Path,
    output_path: Path,
    *,
    slugify: Callable[[str], str] = AnchorSlug.slugify,
) -> tuple[Path, Path]:
    """Return ``(output_dir, expected_markdown_file)`` for a conversion job.

    ``output_path`` may be a directory (writes ``<slug>.md`` inside) or a
    concrete ``.md`` file path.
    """
    if output_path.suffix.lower() == ".md":
        return output_path.parent, output_path
    slug = slugify(source_path.stem)
    return output_path, output_path / f"{slug}.md"


def run_conversion(
    pdf_path: Path,
    output_path: Path,
    *,
    service_factory=build_default_service,
    config_loader=load_config,
) -> ConversionResult:
    """Execute a single PDF → Markdown conversion."""
    pdf = pdf_path.expanduser().resolve()
    if not pdf.is_file():
        msg = f"PDF not found: {pdf}"
        raise FileNotFoundError(msg)

    destination = output_path.expanduser().resolve()
    output_dir, expected_md = resolve_output_paths(pdf, destination)
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = config_loader(None)
    service: ConversionService = service_factory(output_dir=output_dir, config=cfg)
    result = service.convert(
        ConversionRequest(pdf_path=pdf, output_dir=output_dir, config=cfg)
    )

    if result.status != "success" or result.output_path is None:
        return result

    written = Path(result.output_path).resolve()
    expected_md = expected_md.resolve()
    if written != expected_md:
        expected_md.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(written), str(expected_md))
        return ConversionResult(
            status=result.status,
            output_path=expected_md,
            image_count=result.image_count,
            table_count=result.table_count,
            page_count=result.page_count,
            elapsed_seconds=result.elapsed_seconds,
            error=result.error,
            error_message=result.error_message,
        )

    return result


def run_docx_conversion(
    docx_path: Path,
    output_path: Path,
    *,
    service_factory=build_docx_service,
    config: DocxConversionConfig | None = None,
) -> DocxConversionResult:
    """Execute a single DOCX → Markdown conversion."""
    docx = docx_path.expanduser().resolve()
    if not docx.is_file():
        msg = f"DOCX not found: {docx}"
        raise FileNotFoundError(msg)
    if docx.suffix.lower() != ".docx":
        msg = f"file must have .docx extension: {docx}"
        raise ValueError(msg)

    destination = output_path.expanduser().resolve()
    output_dir, expected_md = resolve_output_paths(
        docx,
        destination,
        slugify=DocxAnchorSlug.slugify,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = config or DocxConversionConfig()
    service: DocxConversionService = service_factory(output_dir=output_dir, config=cfg)
    result = service.convert(
        DocxConversionRequest(docx_path=docx, output_dir=output_dir, config=cfg)
    )

    if result.status != "success" or result.output_path is None:
        return result

    written = Path(result.output_path).resolve()
    expected_md = expected_md.resolve()
    if written != expected_md:
        expected_md.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(written), str(expected_md))
        return DocxConversionResult(
            status=result.status,
            output_path=expected_md,
            total_blocks=result.total_blocks,
            headings=result.headings,
            paragraphs=result.paragraphs,
            tables=result.tables,
            images=result.images,
            list_items=result.list_items,
            elapsed_seconds=result.elapsed_seconds,
            error=result.error,
            error_message=result.error_message,
        )

    return result


def format_conversion_result(result: ConversionResult) -> str:
    """Serialize a :class:`ConversionResult` as JSON for MCP tool output."""
    payload = {
        "status": result.status,
        "output_path": str(result.output_path) if result.output_path else None,
        "page_count": result.page_count,
        "image_count": result.image_count,
        "table_count": result.table_count,
        "elapsed_seconds": round(result.elapsed_seconds, 2),
    }
    if result.status != "success":
        payload["error"] = result.error
        payload["error_message"] = result.error_message
    return json.dumps(payload, ensure_ascii=False, indent=2)


def format_docx_conversion_result(result: DocxConversionResult) -> str:
    """Serialize a docx :class:`ConversionResult` as JSON for MCP tool output."""
    payload = {
        "status": result.status,
        "output_path": str(result.output_path) if result.output_path else None,
        "total_blocks": result.total_blocks,
        "headings": result.headings,
        "paragraphs": result.paragraphs,
        "tables": result.tables,
        "images": result.images,
        "list_items": result.list_items,
        "elapsed_seconds": round(result.elapsed_seconds, 2),
    }
    if result.status != "success":
        payload["error"] = result.error
        payload["error_message"] = result.error_message
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool
def convert_pdf_to_markdown(pdf_path: str, output_path: str) -> str:
    """Convert a PDF file to Markdown.

    Args:
        pdf_path: Path to the source PDF file.
        output_path: Output directory or full path to the ``.md`` file.
            When a directory is given, the file is named from the PDF stem
            (e.g. ``book.pdf`` → ``book.md``). Assets are written to
            ``assets/`` under the same directory.

    Returns:
        JSON with ``status``, ``output_path``, page/image/table counts, and
        ``elapsed_seconds``. On failure, includes ``error`` and
        ``error_message``.
    """
    result = run_conversion(Path(pdf_path), Path(output_path))
    if result.status != "success":
        msg = result.error_message or result.error or "conversion failed"
        raise RuntimeError(msg)
    return format_conversion_result(result)


@mcp.tool
def convert_docx_to_markdown(docx_path: str, output_path: str) -> str:
    """Convert a Word (.docx) file to Markdown.

    Args:
        docx_path: Path to the source DOCX file.
        output_path: Output directory or full path to the ``.md`` file.
            When a directory is given, the file is named from the DOCX stem
            (e.g. ``report.docx`` → ``report.md``). Assets are written to
            ``assets/`` under the same directory.

    Returns:
        JSON with ``status``, ``output_path``, block/heading/image/table counts,
        and ``elapsed_seconds``. On failure, includes ``error`` and
        ``error_message``.
    """
    result = run_docx_conversion(Path(docx_path), Path(output_path))
    if result.status != "success":
        msg = result.error_message or result.error or "conversion failed"
        raise RuntimeError(msg)
    return format_docx_conversion_result(result)


def main() -> None:
    """Entry point for ``pdf2md-mcp`` (stdio transport)."""
    mcp.run()


if __name__ == "__main__":
    main()

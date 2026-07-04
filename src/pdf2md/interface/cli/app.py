"""CLI application for pdf2md.

Built with Typer. Provides four subcommands:

- ``convert``  — convert a single PDF.
- ``batch``    — convert a directory of PDFs concurrently.
- ``inspect``  — print structural metadata without writing files.
- ``version``  — print the library version.

All commands respect a ``pdf2md.toml`` configuration file in the
current directory (or the path in ``PDF2MD_CONFIG``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from pdf2md import __version__
from pdf2md.application.dto.dtos import ConversionRequest
from pdf2md.config.config_loader import load_batch_config, load_config
from pdf2md.config.service_factory import build_batch_use_case, build_default_service
from pdf2md.domain.value_objects.enums import ExtractorEngine, HeadingStyle, TableEngine
from pdf2md.domain.value_objects.value_objects import (
    BatchConfig,
    ConversionConfig,
)

app = typer.Typer(
    name="pdf2md",
    help="PDF → Markdown converter for books and documents.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True)


def _setup_logging(verbose: bool) -> None:
    """Configure loguru with a level derived from the verbose flag."""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level, colorize=True)


@app.command()
def version() -> None:
    """Print the pdf2md version and exit."""
    typer.echo(f"pdf2md {__version__}")


def _parse_extractor_engine(value: str) -> ExtractorEngine:
    try:
        return ExtractorEngine(value)
    except ValueError as exc:
        raise typer.BadParameter(
            f"invalid extractor {value!r}; expected pymupdf|pdfplumber"
        ) from exc


@app.command()
def convert(
    pdf: Path = typer.Argument(..., exists=True, readable=True, help="PDF file"),
    output: Path = typer.Option(
        Path("./output"), "--output", "-o", help="Output directory"
    ),
    extractor: str = typer.Option(
        "pymupdf", "--extractor", help="Extraction engine (pymupdf|pdfplumber)"
    ),
    table_extractor: TableEngine = typer.Option(
        TableEngine.PDFPLUMBER, "--table-extractor", help="Table extraction engine"
    ),
    image_min_size: int = typer.Option(
        200, "--image-min-size", help="Minimum image size in pixels"
    ),
    pages: Optional[str] = typer.Option(
        None, "--pages", help="Page range, e.g. 1-50 or 1,3,5"
    ),
    password: Optional[str] = typer.Option(
        None, "--password", help="Password for encrypted PDFs"
    ),
    no_images: bool = typer.Option(False, "--no-images", help="Skip image extraction"),
    no_links: bool = typer.Option(False, "--no-links", help="Skip link extraction"),
    no_tables: bool = typer.Option(False, "--no-tables", help="Skip table extraction"),
    no_frontmatter: bool = typer.Option(
        False, "--no-frontmatter", help="Omit YAML frontmatter"
    ),
    config_path: Optional[Path] = typer.Option(
        None, "--config", help="Path to a pdf2md.toml file"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", is_flag=True),
) -> None:
    """Convert a single PDF to Markdown."""
    _setup_logging(verbose)

    base_config = load_config(config_path)
    cfg = ConversionConfig(
        image_min_size=image_min_size,
        extract_tables=not no_tables,
        table_extractor=table_extractor,
        extract_links=not no_links,
        frontmatter=not no_frontmatter,
        extract_images=not no_images,
        heading_style=base_config.heading_style,
        code_fence=base_config.code_fence,
        assets_subdir=base_config.assets_subdir,
        emit_link_list=base_config.emit_link_list,
        password=password or base_config.password,
        pages_filter=pages or base_config.pages_filter,
        extractor_engine=_parse_extractor_engine(extractor),
        batch_executor=base_config.batch_executor,
    )

    service = build_default_service(output_dir=output, config=cfg)
    request = ConversionRequest(
        pdf_path=pdf,
        output_dir=output,
        config=cfg,
        password=cfg.password,
    )
    result = service.convert(request)

    if result.status == "success":
        console.print(
            f"[bold green]OK[/bold green] wrote [cyan]{result.output_path}[/cyan]"
        )
        console.print(
            f"pages={result.page_count} images={result.image_count} "
            f"tables={result.table_count} elapsed={result.elapsed_seconds:.2f}s"
        )
    else:
        err_console.print(
            f"[bold red]ERROR[/bold red] {result.error}: {result.error_message}"
        )
        raise typer.Exit(code=1)


@app.command()
def batch(
    directory: Path = typer.Argument(..., exists=True, file_okay=False, help="Directory"),
    output: Path = typer.Option(
        Path("./output"), "--output", "-o", help="Output directory"
    ),
    workers: int = typer.Option(2, "--workers", "-w", min=1, help="Worker threads"),
    executor: str = typer.Option(
        "thread", "--executor", help="Batch executor: thread|process"
    ),
    pages: Optional[str] = typer.Option(
        None, "--pages", help="Page range applied to every PDF in the batch"
    ),
    skip_on_error: bool = typer.Option(
        True, "--skip-on-error/--no-skip-on-error", help="Continue batch on failure"
    ),
    report_file: Path = typer.Option(
        Path("batch_report.json"), "--report", help="Path to the JSON report"
    ),
    config_path: Optional[Path] = typer.Option(None, "--config"),
    verbose: bool = typer.Option(False, "--verbose", "-v", is_flag=True),
) -> None:
    """Convert every PDF in a directory."""
    _setup_logging(verbose)

    base_config = load_batch_config(config_path)
    merged_config = ConversionConfig(
        image_min_size=base_config.config.image_min_size,
        extract_tables=base_config.config.extract_tables,
        table_extractor=base_config.config.table_extractor,
        extract_links=base_config.config.extract_links,
        frontmatter=base_config.config.frontmatter,
        extract_images=base_config.config.extract_images,
        heading_style=base_config.config.heading_style,
        code_fence=base_config.config.code_fence,
        assets_subdir=base_config.config.assets_subdir,
        emit_link_list=base_config.config.emit_link_list,
        password=base_config.config.password,
        pages_filter=pages or base_config.config.pages_filter,
        extractor_engine=base_config.extractor,
        batch_executor=executor,
    )
    batch_cfg = BatchConfig(
        workers=workers,
        skip_on_error=skip_on_error,
        report_file=str(report_file),
        pages_filter=pages or base_config.pages_filter,
        extractor=base_config.extractor,
        config=merged_config,
    )
    use_case = build_batch_use_case(output_dir=output, config=merged_config)
    report = use_case.execute(directory, batch_cfg)

    report_file.write_text(report.to_json(), encoding="utf-8")
    console.print(
        f"[bold]Batch finished[/bold] total={report.total} "
        f"success={report.success} failed={report.failed}"
    )
    console.print(f"report written to [cyan]{report_file}[/cyan]")

    if report.failed and not skip_on_error:
        raise typer.Exit(code=1)


@app.command()
def inspect(
    pdf: Path = typer.Argument(..., exists=True, readable=True, help="PDF file"),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output"),
    config_path: Optional[Path] = typer.Option(None, "--config"),
    verbose: bool = typer.Option(False, "--verbose", "-v", is_flag=True),
) -> None:
    """Print structural metadata for a PDF without converting it."""
    _setup_logging(verbose)
    cfg = load_config(config_path)
    service = build_default_service(output_dir=Path("./.inspect_tmp"), config=cfg)
    result = service.inspect(pdf)

    if as_json:
        typer.echo(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return

    table = Table(title=f"Inspection — {pdf.name}")
    table.add_column("Property", style="bold")
    table.add_column("Value")
    for key, value in result.metadata.items():
        if value:
            table.add_row(f"metadata.{key}", str(value))
    table.add_row("page_count", str(result.page_count))
    table.add_row("image_count", str(result.image_count))
    table.add_row("table_count", str(result.table_count))
    for level, count in sorted(result.heading_counts.items()):
        table.add_row(f"headings.H{level}", str(count))
    console.print(table)


def main() -> None:  # noqa: D401 - typer entrypoint
    """Module entrypoint used by the ``pdf2md`` console script."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()

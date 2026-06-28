"""CLI application for xlsx2md.

Built with Typer. Provides three subcommands:

- ``convert``  — convert a single XLSX file.
- ``batch``    — convert a directory of XLSX files concurrently.
- ``version``  — print the library version.
"""

# ruff: noqa: B008 - Typer requires Argument/Option calls in defaults

from __future__ import annotations

import sys
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console

from xlsx2md import __version__
from xlsx2md.application.dto.dtos import ConversionRequest
from xlsx2md.config.service_factory import build_batch_use_case, build_default_service
from xlsx2md.domain.value_objects.value_objects import BatchConfig, ConversionConfig

app = typer.Typer(
    name="xlsx2md",
    help="Excel (.xlsx) → Markdown converter.",
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
    """Print the xlsx2md version and exit."""
    typer.echo(f"xlsx2md {__version__}")


@app.command()
def convert(
    xlsx: Path = typer.Argument(..., exists=True, readable=True, help="XLSX file"),
    output: Path = typer.Option(
        Path("./output"), "--output", "-o", help="Output directory"
    ),
    assets: str = typer.Option("assets", "--assets", help="Assets subdirectory name"),
    no_images: bool = typer.Option(False, "--no-images", help="Skip image extraction"),
    no_index: bool = typer.Option(False, "--no-index", help="Skip index generation"),
    max_rows: int | None = typer.Option(None, "--max-rows", help="Maximum rows per sheet"),
    max_cols: int | None = typer.Option(None, "--max-cols", help="Maximum columns per sheet"),
    no_frontmatter: bool = typer.Option(
        False, "--no-frontmatter", help="Omit YAML frontmatter"
    ),
    no_blocks: bool = typer.Option(
        False, "--no-blocks", help="Disable narrative/table block detection"
    ),
    max_table_cols: int = typer.Option(
        15, "--max-table-cols", help="Default column limit when detecting tables"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", is_flag=True),
) -> None:
    """Convert a single Excel workbook to Markdown (one file per sheet)."""
    _setup_logging(verbose)

    if xlsx.suffix.lower() != ".xlsx":
        err_console.print(f"[bold red]ERROR[/bold red] file must have .xlsx extension: {xlsx}")
        raise typer.Exit(code=1)

    cfg = ConversionConfig(
        assets_subdir=assets,
        extract_images=not no_images,
        include_index=not no_index,
        max_rows=max_rows,
        max_cols=max_cols,
        detect_blocks=not no_blocks,
        default_table_max_cols=max_table_cols,
        frontmatter=not no_frontmatter,
    )

    service = build_default_service(output_dir=output, config=cfg)
    request = ConversionRequest(xlsx_path=xlsx, output_dir=output, config=cfg)
    result = service.convert(request)

    if result.status == "success":
        console.print(
            f"[bold green]OK[/bold green] wrote {len(result.sheet_outputs)} sheet(s)"
        )
        if result.index_path:
            console.print(f"index: [cyan]{result.index_path}[/cyan]")
        for sheet_path in result.sheet_outputs:
            console.print(f"  - [cyan]{sheet_path}[/cyan]")
        console.print(
            f"sheets={result.total_sheets} rows={result.total_rows} "
            f"images={result.total_images} elapsed={result.elapsed_seconds:.2f}s"
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
    skip_on_error: bool = typer.Option(
        True, "--skip-on-error/--no-skip-on-error", help="Continue batch on failure"
    ),
    report_file: Path = typer.Option(
        Path("batch_report.json"), "--report", help="Path to the JSON report"
    ),
    assets: str = typer.Option("assets", "--assets", help="Assets subdirectory name"),
    no_images: bool = typer.Option(False, "--no-images", help="Skip image extraction"),
    no_index: bool = typer.Option(False, "--no-index", help="Skip index generation"),
    max_table_cols: int = typer.Option(
        15, "--max-table-cols", help="Default column limit when detecting tables"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", is_flag=True),
) -> None:
    """Convert every XLSX in a directory."""
    _setup_logging(verbose)

    cfg = ConversionConfig(
        assets_subdir=assets,
        extract_images=not no_images,
        include_index=not no_index,
        default_table_max_cols=max_table_cols,
    )
    batch_cfg = BatchConfig(
        workers=workers,
        skip_on_error=skip_on_error,
        report_file=str(report_file),
        config=cfg,
    )
    use_case = build_batch_use_case(output_dir=output, config=cfg)
    report = use_case.execute(directory, batch_cfg)

    report_file.write_text(report.to_json(), encoding="utf-8")
    console.print(
        f"[bold]Batch finished[/bold] total={report.total} "
        f"success={report.success} failed={report.failed}"
    )
    console.print(f"report written to [cyan]{report_file}[/cyan]")

    if report.failed and not skip_on_error:
        raise typer.Exit(code=1)


def main() -> None:
    """Module entrypoint used by the ``xlsx2md`` console script."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()

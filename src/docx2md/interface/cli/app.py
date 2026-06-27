"""CLI application for docx2md.

Built with Typer. Provides three subcommands:

- ``convert``  — convert a single DOCX file.
- ``batch``    — convert a directory of DOCX files concurrently.
- ``version``  — print the library version.
"""

# ruff: noqa: B008 - Typer requires Argument/Option calls in defaults

from __future__ import annotations

import sys
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console

from docx2md import __version__
from docx2md.application.dto.dtos import ConversionRequest
from docx2md.config.service_factory import build_batch_use_case, build_default_service
from docx2md.domain.value_objects.value_objects import BatchConfig, ConversionConfig

app = typer.Typer(
    name="docx2md",
    help="Word (.docx) → Markdown converter.",
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
    """Print the docx2md version and exit."""
    typer.echo(f"docx2md {__version__}")


@app.command()
def convert(
    docx: Path = typer.Argument(..., exists=True, readable=True, help="DOCX file"),
    output: Path = typer.Option(
        Path("./output"), "--output", "-o", help="Output directory"
    ),
    assets: str = typer.Option("assets", "--assets", help="Assets subdirectory name"),
    no_images: bool = typer.Option(False, "--no-images", help="Skip image extraction"),
    no_frontmatter: bool = typer.Option(
        False, "--no-frontmatter", help="Omit YAML frontmatter"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", is_flag=True),
) -> None:
    """Convert a single Word document to Markdown."""
    _setup_logging(verbose)

    if docx.suffix.lower() != ".docx":
        err_console.print(f"[bold red]ERROR[/bold red] file must have .docx extension: {docx}")
        raise typer.Exit(code=1)

    cfg = ConversionConfig(
        assets_subdir=assets,
        extract_images=not no_images,
        frontmatter=not no_frontmatter,
    )

    service = build_default_service(output_dir=output, config=cfg)
    request = ConversionRequest(docx_path=docx, output_dir=output, config=cfg)
    result = service.convert(request)

    if result.status == "success":
        console.print(
            f"[bold green]OK[/bold green] wrote [cyan]{result.output_path}[/cyan]"
        )
        console.print(
            f"blocks={result.total_blocks} headings={result.headings} "
            f"images={result.images} tables={result.tables} "
            f"elapsed={result.elapsed_seconds:.2f}s"
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
    verbose: bool = typer.Option(False, "--verbose", "-v", is_flag=True),
) -> None:
    """Convert every DOCX in a directory."""
    _setup_logging(verbose)

    cfg = ConversionConfig(assets_subdir=assets)
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
    """Module entrypoint used by the ``docx2md`` console script."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()

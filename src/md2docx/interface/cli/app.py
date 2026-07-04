"""CLI application for md2docx.

Built with Typer. Provides three subcommands:

- ``convert``  — convert Markdown to DOCX.
- ``batch``    — convert a directory of Markdown files concurrently.
- ``version``  — print the library version.
"""

# ruff: noqa: B008 - Typer requires Argument/Option calls in defaults

from __future__ import annotations

import sys
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console

from md2docx import __version__
from md2docx.application.dto.dtos import ConversionRequest
from md2docx.config.service_factory import build_batch_use_case, build_default_service
from md2docx.domain.value_objects.value_objects import BatchConfig, ConversionConfig

app = typer.Typer(
    name="md2docx",
    help="Markdown → Word (.docx) converter.",
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


def _collect_source_paths(md: Path | None, source_dir: Path | None) -> tuple[Path, ...]:
    if source_dir is not None:
        return tuple(sorted(source_dir.rglob("*.md")))
    if md is not None:
        return (md,)
    return ()


@app.command()
def version() -> None:
    """Print the md2docx version and exit."""
    typer.echo(f"md2docx {__version__}")


@app.command()
def convert(
    md: Path | None = typer.Argument(None, exists=True, readable=True, help="Markdown file"),
    output: Path = typer.Option(
        Path("./output"), "--output", "-o", help="Output directory"
    ),
    source_dir: Path | None = typer.Option(
        None,
        "--source-dir",
        "--consolidate-docs",
        exists=True,
        file_okay=False,
        help="Directory of Markdown files to consolidate",
    ),
    reference_docx: Path | None = typer.Option(
        None, "--reference-docx", exists=True, readable=True, help="Custom pandoc reference DOCX"
    ),
    no_consolidate: bool = typer.Option(False, "--no-consolidate", help="Skip multi-file merge"),
    no_toc: bool = typer.Option(False, "--no-toc", help="Skip table of contents insertion"),
    no_clean_tables: bool = typer.Option(
        False, "--no-clean-tables", help="Skip ASCII-art table cleanup"
    ),
    no_refine: bool = typer.Option(
        False, "--no-refine", help="Skip LibreOffice headless refinement"
    ),
    output_docx_name: str = typer.Option(
        "MANUAL_SISTEMA.docx", "--docx-name", help="Output DOCX filename"
    ),
    combined_md_name: str = typer.Option(
        "MANUAL_COMPLETO.md", "--md-name", help="Consolidated Markdown filename"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", is_flag=True),
) -> None:
    """Convert Markdown (single file or consolidated directory) to DOCX."""
    _setup_logging(verbose)

    if md is None and source_dir is None:
        err_console.print(
            "[bold red]ERROR[/bold red] provide a Markdown file or --source-dir"
        )
        raise typer.Exit(code=1)

    if md is not None and md.suffix.lower() != ".md":
        err_console.print(f"[bold red]ERROR[/bold red] file must have .md extension: {md}")
        raise typer.Exit(code=1)

    source_paths = _collect_source_paths(md, source_dir)
    if not source_paths:
        err_console.print("[bold red]ERROR[/bold red] no Markdown files found to convert")
        raise typer.Exit(code=1)

    consolidate = source_dir is not None and not no_consolidate
    cfg = ConversionConfig(
        consolidate=consolidate,
        insert_toc=not no_toc,
        clean_tables=not no_clean_tables,
        refine_with_libreoffice=not no_refine,
        reference_docx=reference_docx,
        output_docx_name=output_docx_name,
        combined_md_name=combined_md_name,
    )

    service = build_default_service(output_dir=output, config=cfg)
    request = ConversionRequest(
        md_path=md if source_dir is None else None,
        output_dir=output,
        source_paths=source_paths if source_dir is not None else (),
        config=cfg,
    )
    result = service.convert(request)

    if result.status == "success":
        console.print(
            f"[bold green]OK[/bold green] wrote [cyan]{result.docx_path}[/cyan]"
        )
        if result.md_path:
            console.print(f"markdown: [cyan]{result.md_path}[/cyan]")
        console.print(
            f"sections={result.sections} refined={result.refined} "
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
    no_refine: bool = typer.Option(
        False, "--no-refine", help="Skip LibreOffice headless refinement"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", is_flag=True),
) -> None:
    """Convert every Markdown file in a directory."""
    _setup_logging(verbose)

    cfg = ConversionConfig(refine_with_libreoffice=not no_refine)
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
    """Module entrypoint used by the ``md2docx`` console script."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()

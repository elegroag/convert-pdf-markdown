"""Domain use cases for MD2DOCX."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import cast

from loguru import logger

from md2docx.domain.exceptions import (
    ConversionError,
    Md2DocxException,
    RenderingError,
    StorageError,
)
from md2docx.domain.ports.ports import (
    IBatchRunner,
    IDocxPostProcessor,
    IManualConsolidator,
    IMarkdownToDocxEngine,
    IReferenceDocxBuilder,
    IStorage,
    ITableCleaner,
    ITocInserter,
)
from md2docx.domain.services.anchor_slug import AnchorSlug
from md2docx.domain.value_objects.value_objects import BatchConfig, ConversionConfig


@dataclass(frozen=True)
class ConvertManualRequest:
    """Input to :class:`ConvertManualUseCase`."""

    md_path: Path | None
    output_dir: Path
    source_paths: tuple[Path, ...] = ()
    config: ConversionConfig = field(default_factory=ConversionConfig)


@dataclass(frozen=True)
class ConvertManualResult:
    """Output of :class:`ConvertManualUseCase`."""

    status: str
    docx_path: Path | None = None
    md_path: Path | None = None
    sections: int = 0
    refined: bool = False
    elapsed_seconds: float = 0.0
    error: str | None = None
    error_message: str = ""


@dataclass(frozen=True)
class BatchItemResult:
    """Per-file result inside a :class:`BatchReport`."""

    file: str
    status: str
    output_path: str | None = None
    error: str | None = None
    message: str = ""
    elapsed_seconds: float = 0.0


@dataclass(frozen=True)
class BatchReport:
    """Aggregate report of a batch run."""

    total: int
    success: int
    failed: int
    results: list[BatchItemResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable dict representation."""
        return {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "results": [
                {
                    "file": r.file,
                    "status": r.status,
                    "output_path": r.output_path,
                    "error": r.error,
                    "message": r.message,
                    "elapsed_seconds": r.elapsed_seconds,
                }
                for r in self.results
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def _resolve_source_paths(request: ConvertManualRequest) -> list[Path]:
    if request.source_paths:
        return list(request.source_paths)
    if request.md_path is not None:
        return [request.md_path]
    return []


class ConvertManualUseCase:
    """Convert Markdown (single or consolidated) to DOCX."""

    def __init__(
        self,
        consolidator: IManualConsolidator,
        table_cleaner: ITableCleaner,
        toc_inserter: ITocInserter,
        reference_builder: IReferenceDocxBuilder,
        pandoc_engine: IMarkdownToDocxEngine,
        post_processor: IDocxPostProcessor,
        storage: IStorage,
    ) -> None:
        self._consolidator = consolidator
        self._table_cleaner = table_cleaner
        self._toc_inserter = toc_inserter
        self._reference_builder = reference_builder
        self._pandoc_engine = pandoc_engine
        self._post_processor = post_processor
        self._storage = storage

    def execute(self, request: ConvertManualRequest) -> ConvertManualResult:
        """Run the Markdown to DOCX pipeline."""
        start = time.perf_counter()
        try:
            paths = _resolve_source_paths(request)
            if not paths:
                raise RenderingError("no Markdown source files provided")

            cfg = request.config
            output_dir = request.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            if len(paths) == 1 and not cfg.consolidate:
                manual = self._consolidator.consolidate(
                    paths,
                    config=replace(cfg, consolidate=False),
                )
            else:
                manual = self._consolidator.consolidate(paths, config=cfg)

            if cfg.clean_tables:
                manual = self._table_cleaner.clean(manual, config=cfg)
            if cfg.insert_toc:
                manual = self._toc_inserter.insert(manual, config=cfg)

            md_path = self._storage.save_manual(manual, output_dir, cfg)
            reference_docx = (
                cfg.reference_docx
                if cfg.reference_docx is not None
                else self._reference_builder.build(output_dir, cfg)
            )

            slug = AnchorSlug.slugify(paths[0].stem)
            intermediate_docx = output_dir / f"{slug}_intermediate.docx"
            pandoc_out = self._pandoc_engine.convert(md_path, reference_docx, intermediate_docx)

            refined = False
            final_docx = pandoc_out
            if cfg.refine_with_libreoffice:
                try:
                    final_docx = self._post_processor.refine(pandoc_out, output_dir)
                    refined = True
                except ConversionError as exc:
                    logger.warning("LibreOffice refine skipped: {}", exc)
                    final_docx = pandoc_out

            docx_path = self._storage.save_docx(final_docx, output_dir, cfg)
            elapsed = time.perf_counter() - start
            return ConvertManualResult(
                status="success",
                docx_path=docx_path,
                md_path=md_path,
                sections=len(manual.sections),
                refined=refined,
                elapsed_seconds=elapsed,
            )
        except (RenderingError, StorageError, ConversionError) as exc:
            return self._failure(exc, start)
        except Md2DocxException as exc:
            logger.exception("md2docx domain error")
            return self._failure(exc, start)
        except Exception as exc:  # noqa: BLE001
            logger.exception("unexpected error during conversion")
            return self._failure(exc, start)

    @staticmethod
    def _failure(exc: Exception, start: float) -> ConvertManualResult:
        return ConvertManualResult(
            status="error",
            elapsed_seconds=time.perf_counter() - start,
            error=type(exc).__name__,
            error_message=str(exc),
        )


class BatchConvertUseCase:
    """Convert every Markdown file in a directory."""

    def __init__(
        self,
        runner: IBatchRunner,
        convert_use_case: ConvertManualUseCase,
        output_dir: Path,
    ) -> None:
        self._runner = runner
        self._convert = convert_use_case
        self._output_dir = output_dir

    def execute(self, directory: Path, config: BatchConfig) -> BatchReport:
        """Run batch conversion for standalone Markdown files."""
        md_files = sorted(directory.rglob("*.md"))
        if not md_files:
            logger.warning("no Markdown files found under {}", directory)
            return BatchReport(total=0, success=0, failed=0)

        def _worker(md_path: Path) -> BatchItemResult:
            slug = AnchorSlug.slugify(md_path.stem)
            out_dir = self._output_dir / slug
            request = ConvertManualRequest(
                md_path=md_path,
                output_dir=out_dir,
                config=replace(config.config, consolidate=False),
            )
            result = self._convert.execute(request)
            return BatchItemResult(
                file=md_path.name,
                status=result.status,
                output_path=str(result.docx_path) if result.docx_path else None,
                error=result.error,
                message=result.error_message,
                elapsed_seconds=result.elapsed_seconds,
            )

        raw_results = self._runner.run(md_files, _worker, workers=config.workers)  # type: ignore[arg-type]
        results = cast(list[BatchItemResult], list(raw_results))
        success = sum(1 for r in results if r.status == "success")
        return BatchReport(
            total=len(results),
            success=success,
            failed=len(results) - success,
            results=results,
        )


__all__ = [
    "BatchConvertUseCase",
    "BatchItemResult",
    "BatchReport",
    "ConvertManualRequest",
    "ConvertManualResult",
    "ConvertManualUseCase",
]

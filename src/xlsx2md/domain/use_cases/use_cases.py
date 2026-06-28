"""Domain use cases for XLSX2MD."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from loguru import logger

from xlsx2md.domain.entities.entities import SheetBlock, XlsxDocument
from xlsx2md.domain.exceptions import (
    CorruptedXlsxError,
    ExtractionError,
    RenderingError,
    StorageError,
    Xlsx2MdException,
)
from xlsx2md.domain.ports.ports import (
    IBatchRunner,
    IIndexRenderer,
    IMarkdownRenderer,
    ISpreadsheetParser,
    IStorage,
)
from xlsx2md.domain.services.anchor_slug import AnchorSlug
from xlsx2md.domain.value_objects.value_objects import BatchConfig, ConversionConfig


@dataclass(frozen=True)
class ConvertSpreadsheetRequest:
    """Input to :class:`ConvertSpreadsheetUseCase`."""

    xlsx_path: Path
    output_dir: Path
    config: ConversionConfig = field(default_factory=ConversionConfig)


@dataclass(frozen=True)
class ConvertSpreadsheetResult:
    """Output of :class:`ConvertSpreadsheetUseCase`."""

    status: str
    sheet_outputs: tuple[Path, ...] = ()
    index_path: Path | None = None
    total_sheets: int = 0
    total_rows: int = 0
    total_images: int = 0
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


def _book_dir(output_dir: Path, xlsx_path: Path) -> Path:
    slug = AnchorSlug.slugify(xlsx_path.stem)
    return output_dir / slug


def _iter_sheets(document: XlsxDocument, config: ConversionConfig) -> list[SheetBlock]:
    sheets = document.sheets
    if config.skip_empty_sheets:
        sheets = [sheet for sheet in sheets if not sheet.is_empty()]
    return sheets


class ConvertSpreadsheetUseCase:
    """Convert a single Excel workbook to Markdown (one file per sheet)."""

    def __init__(
        self,
        parser: ISpreadsheetParser,
        renderer: IMarkdownRenderer,
        index_renderer: IIndexRenderer,
        storage: IStorage,
    ) -> None:
        self._parser = parser
        self._renderer = renderer
        self._index_renderer = index_renderer
        self._storage = storage

    def execute(self, request: ConvertSpreadsheetRequest) -> ConvertSpreadsheetResult:
        """Run the conversion pipeline."""
        start = time.perf_counter()
        try:
            book_dir = _book_dir(request.output_dir, request.xlsx_path)
            document = self._parser.parse(request.xlsx_path, book_dir=book_dir)
            sheets = _iter_sheets(document, request.config)

            sheet_outputs: list[Path] = []
            sheet_files: dict[str, Path] = {}
            total_rows = 0
            total_images = 0

            for sheet in sheets:
                markdown_doc = self._renderer.render(document, sheet)
                markdown_doc.source_xlsx = request.xlsx_path
                output_path = self._storage.save(markdown_doc, source_path=request.xlsx_path)
                sheet_outputs.append(output_path)
                sheet_files[sheet.name] = output_path
                total_rows += sheet.row_count
                total_images += len(sheet.images)

            index_path: Path | None = None
            if request.config.include_index and sheet_files:
                index_doc = self._index_renderer.render(document, sheet_files)
                index_doc.source_xlsx = request.xlsx_path
                index_doc.sheet_name = "_index"
                index_path = self._storage.save(index_doc, source_path=request.xlsx_path)

            elapsed = time.perf_counter() - start
            return ConvertSpreadsheetResult(
                status="success",
                sheet_outputs=tuple(sheet_outputs),
                index_path=index_path,
                total_sheets=len(sheets),
                total_rows=total_rows,
                total_images=total_images,
                elapsed_seconds=elapsed,
            )
        except (CorruptedXlsxError, ExtractionError) as exc:
            return self._failure(exc, start)
        except (RenderingError, StorageError) as exc:
            return self._failure(exc, start)
        except Xlsx2MdException as exc:
            logger.exception("xlsx2md domain error")
            return self._failure(exc, start)
        except Exception as exc:  # noqa: BLE001
            logger.exception("unexpected error during conversion")
            return self._failure(exc, start)

    @staticmethod
    def _failure(exc: Exception, start: float) -> ConvertSpreadsheetResult:
        return ConvertSpreadsheetResult(
            status="error",
            elapsed_seconds=time.perf_counter() - start,
            error=type(exc).__name__,
            error_message=str(exc),
        )


class BatchConvertUseCase:
    """Convert every XLSX in a directory (recursively)."""

    def __init__(
        self,
        runner: IBatchRunner,
        convert_use_case: ConvertSpreadsheetUseCase,
        output_dir: Path,
    ) -> None:
        self._runner = runner
        self._convert = convert_use_case
        self._output_dir = output_dir

    def execute(self, directory: Path, config: BatchConfig) -> BatchReport:
        """Run the batch conversion."""
        xlsx_files = sorted(directory.rglob("*.xlsx"))
        if not xlsx_files:
            logger.warning("no XLSX files found under {}", directory)
            return BatchReport(total=0, success=0, failed=0)

        def _worker(xlsx_path: Path) -> BatchItemResult:
            request = ConvertSpreadsheetRequest(
                xlsx_path=xlsx_path,
                output_dir=self._output_dir,
                config=config.config,
            )
            result = self._convert.execute(request)
            primary_output = str(result.index_path or (result.sheet_outputs[0] if result.sheet_outputs else None))
            return BatchItemResult(
                file=xlsx_path.name,
                status=result.status,
                output_path=primary_output or None,
                error=result.error,
                message=result.error_message,
                elapsed_seconds=result.elapsed_seconds,
            )

        raw_results = self._runner.run(xlsx_files, _worker, workers=config.workers)  # type: ignore[arg-type]
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
    "ConvertSpreadsheetRequest",
    "ConvertSpreadsheetResult",
    "ConvertSpreadsheetUseCase",
]

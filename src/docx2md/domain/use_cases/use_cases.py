"""Domain use cases for DOCX2MD."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from loguru import logger

from docx2md.domain.entities.entities import (
    DocumentBlock,
    HeadingBlock,
    ImageBlock,
    ListItemBlock,
    ParagraphBlock,
    TableBlock,
)
from docx2md.domain.exceptions import (
    CorruptedDocxError,
    Docx2MdException,
    ExtractionError,
    RenderingError,
    StorageError,
)
from docx2md.domain.ports.ports import (
    IBatchRunner,
    IDocumentParser,
    IMarkdownRenderer,
    IStorage,
)
from docx2md.domain.value_objects.value_objects import BatchConfig, ConversionConfig


@dataclass(frozen=True)
class ConvertDocumentRequest:
    """Input to :class:`ConvertDocumentUseCase`."""

    docx_path: Path
    output_dir: Path
    config: ConversionConfig = field(default_factory=ConversionConfig)


@dataclass(frozen=True)
class ConvertDocumentResult:
    """Output of :class:`ConvertDocumentUseCase`."""

    status: str
    output_path: Path | None = None
    total_blocks: int = 0
    headings: int = 0
    paragraphs: int = 0
    tables: int = 0
    images: int = 0
    list_items: int = 0
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


def _count_blocks(blocks: list[DocumentBlock]) -> dict[str, int]:
    return {
        "total_blocks": len(blocks),
        "headings": sum(1 for b in blocks if isinstance(b, HeadingBlock)),
        "paragraphs": sum(1 for b in blocks if isinstance(b, ParagraphBlock)),
        "tables": sum(1 for b in blocks if isinstance(b, TableBlock)),
        "images": sum(1 for b in blocks if isinstance(b, ImageBlock)),
        "list_items": sum(1 for b in blocks if isinstance(b, ListItemBlock)),
    }


class ConvertDocumentUseCase:
    """Convert a single Word document to Markdown."""

    def __init__(
        self,
        parser: IDocumentParser,
        renderer: IMarkdownRenderer,
        storage: IStorage,
    ) -> None:
        self._parser = parser
        self._renderer = renderer
        self._storage = storage

    def execute(self, request: ConvertDocumentRequest) -> ConvertDocumentResult:
        """Run the conversion pipeline."""
        start = time.perf_counter()
        try:
            blocks = list(self._parser.parse(request.docx_path))
            markdown_doc = self._renderer.render(blocks)
            markdown_doc.source_docx = request.docx_path
            output_path = self._storage.save(markdown_doc, source_path=request.docx_path)
            counts = _count_blocks(blocks)
            elapsed = time.perf_counter() - start
            return ConvertDocumentResult(
                status="success",
                output_path=output_path,
                elapsed_seconds=elapsed,
                total_blocks=counts["total_blocks"],
                headings=counts["headings"],
                paragraphs=counts["paragraphs"],
                tables=counts["tables"],
                images=counts["images"],
                list_items=counts["list_items"],
            )
        except (CorruptedDocxError, ExtractionError) as exc:
            return self._failure(exc, start)
        except (RenderingError, StorageError) as exc:
            return self._failure(exc, start)
        except Docx2MdException as exc:
            logger.exception("docx2md domain error")
            return self._failure(exc, start)
        except Exception as exc:  # noqa: BLE001
            logger.exception("unexpected error during conversion")
            return self._failure(exc, start)

    @staticmethod
    def _failure(exc: Exception, start: float) -> ConvertDocumentResult:
        return ConvertDocumentResult(
            status="error",
            elapsed_seconds=time.perf_counter() - start,
            error=type(exc).__name__,
            error_message=str(exc),
        )


class BatchConvertUseCase:
    """Convert every DOCX in a directory (recursively)."""

    def __init__(
        self,
        runner: IBatchRunner,
        convert_use_case: ConvertDocumentUseCase,
    ) -> None:
        self._runner = runner
        self._convert = convert_use_case

    def execute(self, directory: Path, config: BatchConfig) -> BatchReport:
        """Run the batch conversion."""
        docx_files = sorted(directory.rglob("*.docx"))
        if not docx_files:
            logger.warning("no DOCX files found under {}", directory)
            return BatchReport(total=0, success=0, failed=0)

        def _worker(docx_path: Path) -> BatchItemResult:
            request = ConvertDocumentRequest(
                docx_path=docx_path,
                output_dir=docx_path.parent,
                config=config.config,
            )
            result = self._convert.execute(request)
            return BatchItemResult(
                file=docx_path.name,
                status=result.status,
                output_path=str(result.output_path) if result.output_path else None,
                error=result.error,
                message=result.error_message,
                elapsed_seconds=result.elapsed_seconds,
            )

        raw_results = self._runner.run(docx_files, _worker, workers=config.workers)  # type: ignore[arg-type]
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
    "ConvertDocumentRequest",
    "ConvertDocumentResult",
    "ConvertDocumentUseCase",
]

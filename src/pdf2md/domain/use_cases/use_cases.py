"""Domain use cases for PDF2MD.

Use cases orchestrate the flow of data through the application. They
depend only on ports (interfaces), not on concrete infrastructure.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from pdf2md.domain.entities.entities import PdfDocument
from pdf2md.domain.exceptions import (
    CorruptedPdfError,
    EncryptedPdfError,
    ExtractionError,
    Pdf2MdException,
)
from pdf2md.domain.ports.ports import (
    IBatchRunner,
    IExtractor,
    IRenderer,
    IStorage,
)
from pdf2md.domain.value_objects.value_objects import (
    BatchConfig,
    ConversionConfig,
)


@dataclass(frozen=True)
class ConvertPdfRequest:
    """Input to :class:`ConvertPdfUseCase`.

    Attributes:
        pdf_path: The PDF file to convert.
        output_dir: Where to write the Markdown and assets.
        config: Conversion configuration; defaults to library default.
        password: Optional password for encrypted PDFs.
    """

    pdf_path: Path
    output_dir: Path
    config: ConversionConfig = field(default_factory=ConversionConfig)
    password: str | None = None


@dataclass(frozen=True)
class ConvertPdfResult:
    """Output of :class:`ConvertPdfUseCase`.

    Attributes:
        status: ``"success"`` or ``"error"``.
        output_path: Path of the generated ``.md`` file.
        image_count: Number of images extracted.
        table_count: Number of tables extracted.
        page_count: Number of pages rendered.
        elapsed_seconds: Time spent on the conversion.
        error: Exception class name on failure, ``None`` on success.
        error_message: Human-readable error description.
    """

    status: str
    output_path: Path | None = None
    image_count: int = 0
    table_count: int = 0
    page_count: int = 0
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

    def to_dict(self) -> dict:
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


class ConvertPdfUseCase:
    """Convert a single PDF file to Markdown.

    The use case coordinates an :class:`IExtractor`, an :class:`IRenderer`
    and an :class:`IStorage` — all of which are injected. The use case
    is unaware of the concrete implementations.
    """

    def __init__(
        self,
        extractor: IExtractor,
        renderer: IRenderer,
        storage: IStorage,
    ) -> None:
        self._extractor = extractor
        self._renderer = renderer
        self._storage = storage

    def execute(self, request: ConvertPdfRequest) -> ConvertPdfResult:
        """Run the conversion pipeline.

        Args:
            request: The :class:`ConvertPdfRequest` describing the job.

        Returns:
            A :class:`ConvertPdfResult` with status and metrics.
        """
        start = time.perf_counter()
        try:
            document: PdfDocument = self._extractor.extract(request.pdf_path)
            markdown = self._renderer.render(document)
            output_path = self._storage.save(markdown, source=document)
            elapsed = time.perf_counter() - start
            return ConvertPdfResult(
                status="success",
                output_path=output_path,
                image_count=sum(len(p.images) for p in document.pages),
                table_count=sum(len(p.tables) for p in document.pages),
                page_count=document.page_count,
                elapsed_seconds=elapsed,
            )
        except (EncryptedPdfError, CorruptedPdfError) as exc:
            return self._failure(exc, start)
        except ExtractionError as exc:
            return self._failure(exc, start)
        except Pdf2MdException as exc:
            logger.exception("pdf2md domain error")
            return self._failure(exc, start)
        except Exception as exc:  # noqa: BLE001 - we want to capture everything
            logger.exception("unexpected error during conversion")
            return self._failure(exc, start)

    @staticmethod
    def _failure(exc: Exception, start: float) -> ConvertPdfResult:
        return ConvertPdfResult(
            status="error",
            elapsed_seconds=time.perf_counter() - start,
            error=type(exc).__name__,
            error_message=str(exc),
        )


class BatchConvertUseCase:
    """Convert every PDF in a directory (recursively).

    Each file is processed independently — failures are recorded but do
    not stop the batch unless ``BatchConfig.skip_on_error`` is False.
    """

    def __init__(
        self,
        runner: IBatchRunner,
        convert_use_case: ConvertPdfUseCase,
    ) -> None:
        self._runner = runner
        self._convert = convert_use_case

    def execute(
        self,
        directory: Path,
        config: BatchConfig,
    ) -> BatchReport:
        """Run the batch conversion.

        Args:
            directory: Directory containing the PDFs to process.
            config: Batch-level configuration.

        Returns:
            A :class:`BatchReport` with one entry per file.
        """
        pdfs = sorted(directory.rglob("*.pdf"))
        if not pdfs:
            logger.warning("no PDFs found under {}", directory)
            return BatchReport(total=0, success=0, failed=0)

        def _worker(pdf_path: Path) -> BatchItemResult:
            merged = config.config
            if config.pages_filter and not merged.pages_filter:
                merged = ConversionConfig(
                    image_min_size=merged.image_min_size,
                    extract_tables=merged.extract_tables,
                    table_extractor=merged.table_extractor,
                    extract_links=merged.extract_links,
                    frontmatter=merged.frontmatter,
                    extract_images=merged.extract_images,
                    heading_style=merged.heading_style,
                    code_fence=merged.code_fence,
                    assets_subdir=merged.assets_subdir,
                    emit_link_list=merged.emit_link_list,
                    password=merged.password,
                    pages_filter=config.pages_filter,
                    extractor_engine=config.extractor,
                    batch_executor=merged.batch_executor,
                )
            request = ConvertPdfRequest(
                pdf_path=pdf_path,
                output_dir=pdf_path.parent,
                config=merged,
                password=merged.password,
            )
            result = self._convert.execute(request)
            return BatchItemResult(
                file=pdf_path.name,
                status=result.status,
                output_path=str(result.output_path)
                if result.output_path
                else None,
                error=result.error,
                message=result.error_message,
                elapsed_seconds=result.elapsed_seconds,
            )

        results = self._runner.run(pdfs, _worker, workers=config.workers)
        results = list(results)

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
    "ConvertPdfRequest",
    "ConvertPdfResult",
    "ConvertPdfUseCase",
]

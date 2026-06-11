"""Application services.

The :class:`ConversionService` is the public Python entry point. It wires
the domain use case with the injected ports and exposes a friendly API.
"""

from __future__ import annotations

import time
from pathlib import Path

from loguru import logger

from pdf2md.application.dto.dtos import (
    ConversionRequest,
    ConversionResult,
    InspectionResult,
)
from pdf2md.domain.entities.entities import PdfDocument
from pdf2md.domain.ports.ports import IExtractor, IRenderer, IStorage
from pdf2md.domain.use_cases.use_cases import (
    ConvertPdfRequest,
    ConvertPdfResult,
    ConvertPdfUseCase,
)
from pdf2md.domain.value_objects.value_objects import ConversionConfig


class ConversionService:
    """High-level façade for converting a single PDF.

    This is what library users instantiate directly. It owns a configured
    :class:`ConvertPdfUseCase` and translates between public DTOs and
    the domain layer.
    """

    def __init__(
        self,
        extractor: IExtractor,
        renderer: IRenderer,
        storage: IStorage,
        default_config: ConversionConfig | None = None,
    ) -> None:
        self._use_case = ConvertPdfUseCase(extractor, renderer, storage)
        self._extractor = extractor  # kept for inspect()
        self._default_config = default_config or ConversionConfig()

    def convert(self, request: ConversionRequest) -> ConversionResult:
        """Run a single conversion.

        Args:
            request: The :class:`ConversionRequest` describing the job.

        Returns:
            A :class:`ConversionResult` describing the outcome.
        """
        domain_request = ConvertPdfRequest(
            pdf_path=Path(request.pdf_path),
            output_dir=Path(request.output_dir),
            config=request.config or self._default_config,
        )
        domain_result: ConvertPdfResult = self._use_case.execute(domain_request)
        return _to_dto(domain_result)

    def inspect(self, pdf_path: Path) -> InspectionResult:
        """Extract structural metadata without writing any Markdown.

        Args:
            pdf_path: The PDF to inspect.

        Returns:
            An :class:`InspectionResult` with structural counts.
        """
        start = time.perf_counter()
        document: PdfDocument = self._extractor.extract(Path(pdf_path))
        heading_counts: dict[int, int] = {}
        image_count = 0
        table_count = 0
        for page in document.pages:
            for block in page.blocks:
                if block.block_type == "heading" and block.level > 0:
                    heading_counts[block.level] = (
                        heading_counts.get(block.level, 0) + 1
                    )
            image_count += len(page.images)
            table_count += len(page.tables)

        elapsed = time.perf_counter() - start
        logger.debug("inspected {} in {:.2f}s", pdf_path, elapsed)
        return InspectionResult(
            file_path=Path(pdf_path),
            page_count=document.page_count,
            metadata={
                "title": document.metadata.title,
                "author": document.metadata.author,
                "subject": document.metadata.subject,
                "creator": document.metadata.creator,
                "producer": document.metadata.producer,
                "creation_date": document.metadata.creation_date,
            },
            heading_counts=heading_counts,
            image_count=image_count,
            table_count=table_count,
        )


def _to_dto(result: ConvertPdfResult) -> ConversionResult:
    """Map a domain :class:`ConvertPdfResult` to a public DTO."""
    return ConversionResult(
        status=result.status,
        output_path=result.output_path,
        image_count=result.image_count,
        table_count=result.table_count,
        page_count=result.page_count,
        elapsed_seconds=result.elapsed_seconds,
        error=result.error,
        error_message=result.error_message,
    )


__all__ = ["ConversionService"]

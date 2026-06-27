"""Application services for DOCX2MD."""

from __future__ import annotations

import time
from pathlib import Path

from loguru import logger

from docx2md.application.dto.dtos import (
    ConversionRequest,
    ConversionResult,
    InspectionResult,
)
from docx2md.domain.entities.entities import (
    HeadingBlock,
    ImageBlock,
    ListItemBlock,
    ParagraphBlock,
    TableBlock,
)
from docx2md.domain.ports.ports import IDocumentParser, IMarkdownRenderer, IStorage
from docx2md.domain.use_cases.use_cases import (
    ConvertDocumentRequest,
    ConvertDocumentResult,
    ConvertDocumentUseCase,
)
from docx2md.domain.value_objects.value_objects import ConversionConfig


class ConversionService:
    """High-level façade for converting a single Word document."""

    def __init__(
        self,
        parser: IDocumentParser,
        renderer: IMarkdownRenderer,
        storage: IStorage,
        default_config: ConversionConfig | None = None,
    ) -> None:
        self._use_case = ConvertDocumentUseCase(parser, renderer, storage)
        self._parser = parser
        self._default_config = default_config or ConversionConfig()

    def convert(self, request: ConversionRequest) -> ConversionResult:
        """Run a single conversion."""
        domain_request = ConvertDocumentRequest(
            docx_path=Path(request.docx_path),
            output_dir=Path(request.output_dir),
            config=request.config or self._default_config,
        )
        domain_result: ConvertDocumentResult = self._use_case.execute(domain_request)
        return _to_dto(domain_result)

    def inspect(self, docx_path: Path) -> InspectionResult:
        """Extract structural metadata without writing Markdown."""
        start = time.perf_counter()
        blocks = list(self._parser.parse(Path(docx_path)))
        heading_counts: dict[int, int] = {}
        for block in blocks:
            if isinstance(block, HeadingBlock):
                heading_counts[block.level] = heading_counts.get(block.level, 0) + 1
        elapsed = time.perf_counter() - start
        logger.debug("inspected {} in {:.2f}s", docx_path, elapsed)
        return InspectionResult(
            file_path=Path(docx_path),
            total_blocks=len(blocks),
            heading_counts=heading_counts,
            paragraph_count=sum(1 for b in blocks if isinstance(b, ParagraphBlock)),
            image_count=sum(1 for b in blocks if isinstance(b, ImageBlock)),
            table_count=sum(1 for b in blocks if isinstance(b, TableBlock)),
            list_item_count=sum(1 for b in blocks if isinstance(b, ListItemBlock)),
        )


def _to_dto(result: ConvertDocumentResult) -> ConversionResult:
    """Map a domain result to a public DTO."""
    return ConversionResult(
        status=result.status,
        output_path=result.output_path,
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


__all__ = ["ConversionService"]

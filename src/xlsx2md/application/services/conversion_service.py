"""Application services for XLSX2MD."""

from __future__ import annotations

import time
from pathlib import Path

from loguru import logger

from xlsx2md.application.dto.dtos import (
    ConversionRequest,
    ConversionResult,
    InspectionResult,
)
from xlsx2md.domain.ports.ports import IIndexRenderer, IMarkdownRenderer, ISpreadsheetParser, IStorage
from xlsx2md.domain.services.anchor_slug import AnchorSlug
from xlsx2md.domain.use_cases.use_cases import (
    ConvertSpreadsheetRequest,
    ConvertSpreadsheetResult,
    ConvertSpreadsheetUseCase,
)
from xlsx2md.domain.value_objects.value_objects import ConversionConfig


class ConversionService:
    """High-level façade for converting a single Excel workbook."""

    def __init__(
        self,
        parser: ISpreadsheetParser,
        renderer: IMarkdownRenderer,
        index_renderer: IIndexRenderer,
        storage: IStorage,
        default_config: ConversionConfig | None = None,
    ) -> None:
        self._use_case = ConvertSpreadsheetUseCase(parser, renderer, index_renderer, storage)
        self._parser = parser
        self._default_config = default_config or ConversionConfig()

    def convert(self, request: ConversionRequest) -> ConversionResult:
        """Run a single conversion."""
        domain_request = ConvertSpreadsheetRequest(
            xlsx_path=Path(request.xlsx_path),
            output_dir=Path(request.output_dir),
            config=request.config or self._default_config,
        )
        domain_result: ConvertSpreadsheetResult = self._use_case.execute(domain_request)
        return _to_dto(domain_result)

    def inspect(self, xlsx_path: Path, output_dir: Path | None = None) -> InspectionResult:
        """Extract structural metadata without writing Markdown."""
        start = time.perf_counter()
        book_dir = (output_dir or xlsx_path.parent) / AnchorSlug.slugify(xlsx_path.stem)
        document = self._parser.parse(Path(xlsx_path), book_dir=book_dir)
        non_empty = [sheet for sheet in document.sheets if not sheet.is_empty()]
        total_rows = sum(sheet.row_count for sheet in non_empty)
        total_images = sum(len(sheet.images) for sheet in non_empty)
        elapsed = time.perf_counter() - start
        logger.debug("inspected {} in {:.2f}s", xlsx_path, elapsed)
        sheet_kinds = []
        for sheet in document.sheets:
            kind = type(sheet).__name__
            sheet_kinds.append(f"{sheet.name}:{kind}")
        return InspectionResult(
            file_path=Path(xlsx_path),
            total_sheets=len(document.sheets),
            sheet_names=tuple(sheet.name for sheet in document.sheets),
            non_empty_sheets=len(non_empty),
            total_rows=total_rows,
            total_images=total_images,
        )


def _to_dto(result: ConvertSpreadsheetResult) -> ConversionResult:
    """Map a domain result to a public DTO."""
    return ConversionResult(
        status=result.status,
        sheet_outputs=result.sheet_outputs,
        index_path=result.index_path,
        total_sheets=result.total_sheets,
        total_rows=result.total_rows,
        total_images=result.total_images,
        elapsed_seconds=result.elapsed_seconds,
        error=result.error,
        error_message=result.error_message,
    )


__all__ = ["ConversionService"]

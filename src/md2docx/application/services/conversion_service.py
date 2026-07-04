"""Application services for MD2DOCX."""

from __future__ import annotations

import re
import time
from pathlib import Path

from loguru import logger

from md2docx.application.dto.dtos import ConversionRequest, ConversionResult, InspectionResult
from md2docx.domain.ports.ports import IMarkdownReader
from md2docx.domain.use_cases.use_cases import (
    ConvertManualRequest,
    ConvertManualResult,
    ConvertManualUseCase,
)
from md2docx.domain.value_objects.value_objects import ConversionConfig


class ConversionService:
    """High-level façade for converting Markdown to DOCX."""

    def __init__(
        self,
        use_case: ConvertManualUseCase,
        reader: IMarkdownReader,
        default_config: ConversionConfig | None = None,
    ) -> None:
        self._use_case = use_case
        self._reader = reader
        self._default_config = default_config or ConversionConfig()

    def convert(self, request: ConversionRequest) -> ConversionResult:
        """Run a single conversion."""
        domain_request = ConvertManualRequest(
            md_path=request.md_path,
            output_dir=Path(request.output_dir),
            source_paths=request.source_paths,
            config=request.config or self._default_config,
        )
        domain_result: ConvertManualResult = self._use_case.execute(domain_request)
        return _to_dto(domain_result)

    def inspect(self, md_path: Path, *, delimiter: str = "=" * 60) -> InspectionResult:
        """Extract structural metadata without writing DOCX."""
        start = time.perf_counter()
        content = self._reader.read(Path(md_path))
        lines = content.splitlines()
        heading_count = sum(1 for line in lines if line.strip().startswith("#"))
        table_line_count = sum(1 for line in lines if line.strip().startswith("|"))
        pattern = re.escape(delimiter) + r"\n(.+?)\n" + re.escape(delimiter)
        section_count = len(re.findall(pattern, content, re.DOTALL))
        elapsed = time.perf_counter() - start
        logger.debug("inspected {} in {:.2f}s", md_path, elapsed)
        return InspectionResult(
            file_path=Path(md_path),
            line_count=len(lines),
            heading_count=heading_count,
            table_line_count=table_line_count,
            section_count=section_count,
        )


def _to_dto(result: ConvertManualResult) -> ConversionResult:
    """Map a domain result to a public DTO."""
    return ConversionResult(
        status=result.status,
        docx_path=result.docx_path,
        md_path=result.md_path,
        sections=result.sections,
        refined=result.refined,
        elapsed_seconds=result.elapsed_seconds,
        error=result.error,
        error_message=result.error_message,
    )


__all__ = ["ConversionService"]

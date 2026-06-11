"""Factory for the default :class:`ConversionService`.

Wires the default PyMuPDF extractor, Markdown renderer, and file
storage. The batch use case and its runner are also built here so the
CLI can resolve them from one place.
"""

from __future__ import annotations

from pathlib import Path

from pdf2md.application.dto.dtos import ConversionRequest
from pdf2md.application.services.conversion_service import ConversionService
from pdf2md.domain.use_cases.use_cases import BatchConvertUseCase
from pdf2md.domain.value_objects.value_objects import ConversionConfig
from pdf2md.infrastructure.extractors.pdfplumber_extractor import (
    PdfplumberTableExtractor,
)
from pdf2md.infrastructure.extractors.pymupdf_extractor import PyMuPdfExtractor
from pdf2md.infrastructure.renderers.markdown_renderer import MarkdownRenderer
from pdf2md.infrastructure.storage.batch_runner import ThreadPoolBatchRunner
from pdf2md.infrastructure.storage.file_storage import FileStorage


def build_default_service(
    output_dir: Path,
    config: ConversionConfig | None = None,
) -> ConversionService:
    """Build a fully-wired :class:`ConversionService` with default adapters.

    Args:
        output_dir: Directory where the Markdown and assets will be written.
        config: Optional :class:`ConversionConfig`.

    Returns:
        A ready-to-use :class:`ConversionService`.
    """
    cfg = config or ConversionConfig()
    extractor = PyMuPdfExtractor(
        config=cfg,
        table_extractor=PdfplumberTableExtractor(),
    )
    renderer = MarkdownRenderer(cfg)
    storage = FileStorage(output_dir=output_dir, config=cfg)
    return ConversionService(
        extractor=extractor,
        renderer=renderer,
        storage=storage,
        default_config=cfg,
    )


def build_batch_use_case(
    output_dir: Path,
    config: ConversionConfig | None = None,
) -> BatchConvertUseCase:
    """Build a :class:`BatchConvertUseCase` with all dependencies wired.

    The batch use case reuses the same default service for every PDF.
    """
    service = build_default_service(output_dir, config)
    runner = ThreadPoolBatchRunner()
    # We pass the inner use case so the batch reuses the configured
    # pipeline (extractor, renderer, storage) without re-building it.
    return BatchConvertUseCase(
        runner=runner,
        convert_use_case=service._use_case,  # noqa: SLF001 - intentional
    )


__all__ = ["build_batch_use_case", "build_default_service"]


# Re-export the DTOs at the top level for convenience.
__all__ += ["ConversionRequest"]

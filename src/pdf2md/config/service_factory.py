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
from pdf2md.domain.value_objects.enums import ExtractorEngine
from pdf2md.domain.value_objects.value_objects import ConversionConfig
from pdf2md.infrastructure.extractors.pymupdf_extractor import PyMuPdfExtractor
from pdf2md.infrastructure.extractors.table_extractor_factory import (
    build_default_table_extractor,
)
from pdf2md.infrastructure.renderers.markdown_renderer import MarkdownRenderer
from pdf2md.infrastructure.storage.batch_runner import (
    ProcessPoolBatchRunner,
    ThreadPoolBatchRunner,
)
from pdf2md.infrastructure.storage.file_storage import FileStorage


def build_default_service(
    output_dir: Path,
    config: ConversionConfig | None = None,
) -> ConversionService:
    """Build a fully-wired :class:`ConversionService` with default adapters."""
    cfg = config or ConversionConfig()
    if cfg.extractor_engine != ExtractorEngine.PYMUPDF:
        raise ValueError(
            f"extractor engine {cfg.extractor_engine.value!r} is not implemented; "
            "use pymupdf"
        )
    table_extractor = build_default_table_extractor(cfg.table_extractor)
    extractor = PyMuPdfExtractor(
        config=cfg,
        table_extractor=table_extractor,
    )
    renderer = MarkdownRenderer(cfg)
    storage = FileStorage(output_dir=output_dir, config=cfg)
    return ConversionService(
        extractor=extractor,
        renderer=renderer,
        storage=storage,
        default_config=cfg,
    )


def build_batch_runner(config: ConversionConfig | None = None) -> ThreadPoolBatchRunner | ProcessPoolBatchRunner:
    """Return the configured batch runner implementation."""
    cfg = config or ConversionConfig()
    if cfg.batch_executor == "process":
        return ProcessPoolBatchRunner()
    return ThreadPoolBatchRunner()


def build_batch_use_case(
    output_dir: Path,
    config: ConversionConfig | None = None,
) -> BatchConvertUseCase:
    """Build a :class:`BatchConvertUseCase` with all dependencies wired."""
    cfg = config or ConversionConfig()
    service = build_default_service(output_dir, cfg)
    runner = build_batch_runner(cfg)
    return BatchConvertUseCase(
        runner=runner,
        convert_use_case=service._use_case,  # noqa: SLF001 - intentional
    )


__all__ = [
    "build_batch_runner",
    "build_batch_use_case",
    "build_default_service",
    "ConversionRequest",
]

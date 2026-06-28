"""Factory for the default :class:`ConversionService`."""

from __future__ import annotations

from pathlib import Path

from xlsx2md.application.services.conversion_service import ConversionService
from xlsx2md.domain.use_cases.use_cases import BatchConvertUseCase
from xlsx2md.domain.value_objects.value_objects import ConversionConfig
from xlsx2md.infrastructure.parsers.xlsx_parser import XlsxParser
from xlsx2md.infrastructure.renderers.index_renderer import IndexRenderer
from xlsx2md.infrastructure.renderers.markdown_renderer import MarkdownRenderer
from xlsx2md.infrastructure.storage.batch_runner import ThreadPoolBatchRunner
from xlsx2md.infrastructure.storage.file_storage import FileStorage


def build_default_service(
    output_dir: Path,
    config: ConversionConfig | None = None,
) -> ConversionService:
    """Build a fully-wired :class:`ConversionService` with default adapters."""
    cfg = config or ConversionConfig()
    parser = XlsxParser(config=cfg)
    renderer = MarkdownRenderer(cfg)
    index_renderer = IndexRenderer(cfg)
    storage = FileStorage(output_dir=output_dir, config=cfg)
    return ConversionService(
        parser=parser,
        renderer=renderer,
        index_renderer=index_renderer,
        storage=storage,
        default_config=cfg,
    )


def build_batch_use_case(
    output_dir: Path,
    config: ConversionConfig | None = None,
) -> BatchConvertUseCase:
    """Build a :class:`BatchConvertUseCase` with all dependencies wired."""
    service = build_default_service(output_dir, config)
    runner = ThreadPoolBatchRunner()
    return BatchConvertUseCase(
        runner=runner,
        convert_use_case=service._use_case,  # noqa: SLF001 - intentional
        output_dir=output_dir,
    )


__all__ = ["build_batch_use_case", "build_default_service"]

"""Factory for the default :class:`ConversionService`."""

from __future__ import annotations

from pathlib import Path

from md2docx.application.services.conversion_service import ConversionService
from md2docx.domain.services.manual_consolidator import ManualConsolidator
from md2docx.domain.services.table_cleaner import TableCleaner
from md2docx.domain.services.toc_inserter import TocInserter
from md2docx.domain.use_cases.use_cases import BatchConvertUseCase, ConvertManualUseCase
from md2docx.domain.value_objects.value_objects import ConversionConfig
from md2docx.infrastructure.builders.docx_style_builder import DocxStyleBuilder
from md2docx.infrastructure.engines.libreoffice_postprocessor import LibreOfficePostProcessor
from md2docx.infrastructure.engines.pandoc_engine import PandocEngine
from md2docx.infrastructure.readers.file_markdown_reader import FileMarkdownReader
from md2docx.infrastructure.storage.batch_runner import ThreadPoolBatchRunner
from md2docx.infrastructure.storage.file_storage import FileStorage


def build_default_service(
    output_dir: Path,
    config: ConversionConfig | None = None,
) -> ConversionService:
    """Build a fully-wired :class:`ConversionService` with default adapters."""
    cfg = config or ConversionConfig()
    reader = FileMarkdownReader()
    use_case = ConvertManualUseCase(
        consolidator=ManualConsolidator(),
        table_cleaner=TableCleaner(),
        toc_inserter=TocInserter(),
        reference_builder=DocxStyleBuilder(),
        pandoc_engine=PandocEngine(),
        post_processor=LibreOfficePostProcessor(),
        storage=FileStorage(),
    )
    return ConversionService(
        use_case=use_case,
        reader=reader,
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

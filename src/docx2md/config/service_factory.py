"""Factory for the default :class:`ConversionService`."""

from __future__ import annotations

from pathlib import Path

from docx2md.application.services.conversion_service import ConversionService
from docx2md.domain.use_cases.use_cases import BatchConvertUseCase
from docx2md.domain.value_objects.value_objects import ConversionConfig
from docx2md.infrastructure.parsers.docx_parser import DocxParser
from docx2md.infrastructure.renderers.markdown_renderer import MarkdownRenderer
from docx2md.infrastructure.storage.asset_exporter import FileAssetExporter
from docx2md.infrastructure.storage.batch_runner import ThreadPoolBatchRunner
from docx2md.infrastructure.storage.file_storage import FileStorage


def build_default_service(
    output_dir: Path,
    config: ConversionConfig | None = None,
) -> ConversionService:
    """Build a fully-wired :class:`ConversionService` with default adapters."""
    cfg = config or ConversionConfig()
    assets_dir = Path(output_dir) / cfg.assets_subdir
    asset_exporter = FileAssetExporter(assets_dir=assets_dir, config=cfg)
    parser = DocxParser(asset_exporter=asset_exporter, config=cfg)
    renderer = MarkdownRenderer(cfg)
    storage = FileStorage(output_dir=output_dir, config=cfg)
    return ConversionService(
        parser=parser,
        renderer=renderer,
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
    )


__all__ = ["build_batch_use_case", "build_default_service"]

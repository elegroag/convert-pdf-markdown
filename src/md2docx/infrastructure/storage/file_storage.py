"""Filesystem storage adapter for MD2DOCX."""

from __future__ import annotations

import shutil
from pathlib import Path

from loguru import logger

from md2docx.domain.entities.entities import ConsolidatedManual
from md2docx.domain.exceptions import StorageError
from md2docx.domain.ports.ports import IStorage
from md2docx.domain.value_objects.value_objects import ConversionConfig


class FileStorage(IStorage):
    """Persist consolidated Markdown and final DOCX."""

    def save_manual(
        self,
        manual: ConsolidatedManual,
        output_dir: Path,
        config: ConversionConfig,
    ) -> Path:
        """Write consolidated Markdown to disk."""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            md_path = output_dir / config.combined_md_name
            md_path.write_text(manual.combined, encoding="utf-8")
            logger.info("wrote consolidated markdown {}", md_path)
            return md_path
        except OSError as exc:
            raise StorageError(f"failed to write markdown: {exc}") from exc

    def save_docx(
        self,
        source_docx: Path,
        output_dir: Path,
        config: ConversionConfig,
    ) -> Path:
        """Copy the DOCX to the configured output filename."""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            target = output_dir / config.output_docx_name
            if source_docx.resolve() != target.resolve():
                shutil.copy2(source_docx, target)
            logger.info("wrote docx {}", target)
            return target
        except OSError as exc:
            raise StorageError(f"failed to write docx: {exc}") from exc


__all__ = ["FileStorage"]

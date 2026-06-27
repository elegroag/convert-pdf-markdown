"""Filesystem-based storage adapter for DOCX2MD."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from docx2md.domain.entities.entities import MarkdownDocument
from docx2md.domain.exceptions import StorageError
from docx2md.domain.ports.ports import IStorage
from docx2md.domain.services.anchor_slug import AnchorSlug
from docx2md.domain.value_objects.value_objects import ConversionConfig


class FileStorage(IStorage):
    """Persist a Markdown document to disk."""

    def __init__(
        self,
        output_dir: Path,
        config: ConversionConfig | None = None,
    ) -> None:
        self._output_dir = Path(output_dir)
        self._config = config or ConversionConfig()

    @property
    def output_dir(self) -> Path:
        """The root output directory."""
        return self._output_dir

    def save(self, document: MarkdownDocument, source_path: Path) -> Path:
        """Save the Markdown document and return the output path."""
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            slug = AnchorSlug.slugify(source_path.stem)
            output_path = self._output_dir / f"{slug}.md"
            assets_dir = self._output_dir / self._config.assets_subdir
            output_path.write_text(document.to_string(), encoding="utf-8")
            document.output_path = output_path
            document.assets_dir = assets_dir if assets_dir.exists() else None
            logger.info("wrote markdown {}", output_path)
            return output_path
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError(f"failed to write {source_path}: {exc}") from exc


__all__ = ["FileStorage"]

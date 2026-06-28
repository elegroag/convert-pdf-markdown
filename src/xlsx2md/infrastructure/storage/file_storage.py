"""Filesystem-based storage adapter for XLSX2MD."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from xlsx2md.domain.entities.entities import MarkdownDocument
from xlsx2md.domain.exceptions import StorageError
from xlsx2md.domain.ports.ports import IStorage
from xlsx2md.domain.services.anchor_slug import AnchorSlug
from xlsx2md.domain.value_objects.value_objects import ConversionConfig


class FileStorage(IStorage):
    """Persist Markdown documents for a workbook."""

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
            book_slug = AnchorSlug.slugify(source_path.stem)
            book_dir = self._output_dir / book_slug
            book_dir.mkdir(parents=True, exist_ok=True)

            if document.sheet_name == "_index":
                output_path = book_dir / "_index.md"
            else:
                sheet_slug = AnchorSlug.slugify(document.sheet_name)
                output_path = book_dir / f"{sheet_slug}.md"

            assets_dir = book_dir / self._config.assets_subdir
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

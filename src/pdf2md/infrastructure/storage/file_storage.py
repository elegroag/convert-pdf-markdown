"""Filesystem-based storage adapter."""

from __future__ import annotations

from pathlib import Path

from loguru import logger

from pdf2md.domain.entities.entities import (
    ImageAsset,
    MarkdownDocument,
    PdfDocument,
)
from pdf2md.domain.exceptions import StorageError
from pdf2md.domain.ports.ports import IStorage
from pdf2md.domain.value_objects.value_objects import ConversionConfig

from pdf2md.domain.services.anchor_slug import AnchorSlug


class FileStorage(IStorage):
    """Persist a :class:`MarkdownDocument` and its image assets to disk.

    The Markdown file is written to ``<output_dir>/<slug>.md`` and
    image assets are written to ``<output_dir>/<assets_subdir>/``.
    The ``output_path`` of each image is set on the original
    :class:`ImageAsset` so downstream code can reference it.
    """

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

    def save(
        self,
        document: MarkdownDocument,
        source: PdfDocument | None = None,
    ) -> Path:
        """Save the Markdown document and image assets to disk.

        Args:
            document: The rendered Markdown document.
            source: The original PDF document with image bytes. Optional —
                ``InMemoryStorage`` and tests may not provide one.

        Returns:
            The path of the generated ``.md`` file.

        Raises:
            StorageError: If writing to disk fails.
        """
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            slug = AnchorSlug.slugify(document.source_pdf.stem)
            output_path = self._output_dir / f"{slug}.md"
            assets_dir = self._output_dir / self._config.assets_subdir

            has_images = bool(source and any(p.images for p in source.pages))
            if has_images:
                assets_dir.mkdir(parents=True, exist_ok=True)
                self._write_assets(source, slug, assets_dir)  # type: ignore[arg-type]

            output_path.write_text(document.to_string(), encoding="utf-8")
            document.output_path = output_path
            document.assets_dir = assets_dir if has_images else None
            logger.info("wrote markdown {}", output_path)
            return output_path
        except StorageError:
            raise
        except OSError as exc:
            raise StorageError(
                f"failed to write {document.source_pdf}: {exc}"
            ) from exc

    def _write_assets(
        self,
        source: PdfDocument,
        slug: str,
        assets_dir: Path,
    ) -> None:
        """Write every image byte in the source document to ``assets_dir``."""
        for page in source.pages:
            for image in page.images:
                ext = (image.format or "png").lower()
                if ext == "jpeg":
                    ext = "jpg"
                name = f"{image.image_id}.{ext}"
                target = assets_dir / name
                target.write_bytes(image.raw_bytes)
                image.output_path = target
                logger.debug("wrote image asset {}", target)


__all__ = ["FileStorage"]

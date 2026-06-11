"""Unit tests for the storage adapters."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pdf2md.domain.entities.entities import (
    ImageAsset,
    MarkdownDocument,
    MarkdownPage,
    PdfDocument,
    PdfPage,
)
from pdf2md.domain.exceptions import StorageError
from pdf2md.domain.value_objects.value_objects import ConversionConfig
from pdf2md.infrastructure.storage.file_storage import FileStorage
from pdf2md.infrastructure.storage.in_memory_storage import InMemoryStorage


def _doc_with_image() -> PdfDocument:
    image = ImageAsset(
        image_id="p1_img1",
        page_number=1,
        bbox=(0, 0, 10, 10),
        format="PNG",
        raw_bytes=b"\x89PNG\r\n\x1a\n",
    )
    return PdfDocument(
        file_path=Path("book.pdf"),
        page_count=1,
        pages=[PdfPage(page_number=1, images=[image])],
    )


def _markdown_doc() -> MarkdownDocument:
    return MarkdownDocument(
        source_pdf=Path("book.pdf"),
        pages=[MarkdownPage(page_number=1, content="# Title\n")],
    )


class TestFileStorage:
    """``FileStorage`` writes the Markdown and image assets to disk."""

    def test_save_creates_markdown_file(self, tmp_path: Path) -> None:
        """The Markdown file is written to ``<output_dir>/<slug>.md``."""
        storage = FileStorage(output_dir=tmp_path)
        out = storage.save(_markdown_doc(), source=_doc_with_image())
        assert out.is_file()
        assert "# Title" in out.read_text(encoding="utf-8")

    def test_save_writes_image_assets(self, tmp_path: Path) -> None:
        """Image bytes are written to ``<output_dir>/<assets_subdir>/``."""
        storage = FileStorage(output_dir=tmp_path)
        doc = _doc_with_image()
        storage.save(_markdown_doc(), source=doc)
        assets = list((tmp_path / "assets").iterdir())
        assert len(assets) == 1
        assert assets[0].read_bytes() == b"\x89PNG\r\n\x1a\n"
        # The asset has its ``output_path`` set on the original entity.
        assert doc.pages[0].images[0].output_path is not None

    def test_save_creates_output_directory(self, tmp_path: Path) -> None:
        """The output directory is created if it does not exist."""
        out_dir = tmp_path / "does_not_exist" / "output"
        storage = FileStorage(output_dir=out_dir)
        storage.save(_markdown_doc(), source=_doc_with_image())
        assert out_dir.is_dir()

    def test_save_without_source_omits_assets(self, tmp_path: Path) -> None:
        """If no source PDF is provided, only the Markdown file is written."""
        storage = FileStorage(output_dir=tmp_path)
        storage.save(_markdown_doc(), source=None)
        assert (tmp_path / "book.md").is_file()
        # No assets subdir gets created when there are no images.
        assert not (tmp_path / "assets").exists()

    def test_save_writes_jpeg_extension(self, tmp_path: Path) -> None:
        """JPEG images are written with the ``.jpg`` extension."""
        storage = FileStorage(output_dir=tmp_path)
        source = PdfDocument(
            file_path=Path("b.pdf"),
            page_count=1,
            pages=[
                PdfPage(
                    page_number=1,
                    images=[
                        ImageAsset(
                            image_id="p1_img1",
                            page_number=1,
                            bbox=(0, 0, 10, 10),
                            format="JPEG",
                            raw_bytes=b"\xff\xd8\xff",
                        )
                    ],
                )
            ],
        )
        md = MarkdownDocument(source_pdf=Path("b.pdf"))
        storage.save(md, source=source)
        assert (tmp_path / "assets" / "p1_img1.jpg").is_file()

    def test_save_wraps_oserror_as_storage_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``OSError`` from the filesystem becomes a ``StorageError``."""
        storage = FileStorage(output_dir=tmp_path)
        # Force an OSError by monkey-patching ``Path.mkdir`` for this dir.
        def _raise(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            raise OSError("simulated")
        monkeypatch.setattr(Path, "mkdir", _raise)
        with pytest.raises(StorageError):
            storage.save(_markdown_doc(), source=None)

    def test_assets_subdir_configurable(self, tmp_path: Path) -> None:
        """A custom assets_subdir is respected."""
        storage = FileStorage(
            output_dir=tmp_path,
            config=ConversionConfig(assets_subdir="images"),
        )
        storage.save(_markdown_doc(), source=_doc_with_image())
        assert (tmp_path / "images").is_dir()


class TestInMemoryStorage:
    """``InMemoryStorage`` keeps everything in RAM."""

    def test_save_stores_markdown(self) -> None:
        """The rendered Markdown is stored in ``self.markdown``."""
        storage = InMemoryStorage()
        storage.save(_markdown_doc(), source=None)
        assert "# Title" in storage.markdown

    def test_save_collects_image_bytes(self) -> None:
        """Image bytes from the source are stored in ``self.images``."""
        storage = InMemoryStorage()
        storage.save(_markdown_doc(), source=_doc_with_image())
        assert "p1_img1" in storage.images
        assert storage.images["p1_img1"] == b"\x89PNG\r\n\x1a\n"

    def test_last_output_is_virtual_path(self) -> None:
        """The saved path is a ``memory:`` URL."""
        storage = InMemoryStorage()
        out = storage.save(_markdown_doc(), source=None)
        assert str(out).startswith("memory:")
        assert "book.md" in str(out)

    def test_open_markdown_returns_stream(self) -> None:
        """``open_markdown`` yields a readable text stream."""
        storage = InMemoryStorage()
        storage.save(_markdown_doc(), source=None)
        with storage.open_markdown() as f:
            content = f.read()
        assert "# Title" in content

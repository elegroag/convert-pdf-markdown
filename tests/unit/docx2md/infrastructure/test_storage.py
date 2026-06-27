"""Tests for docx2md storage adapters."""

from __future__ import annotations

from pathlib import Path

from docx2md.domain.entities.entities import MarkdownDocument
from docx2md.infrastructure.storage.asset_exporter import FileAssetExporter
from docx2md.infrastructure.storage.file_storage import FileStorage


class TestFileAssetExporter:
    def test_exports_bytes(self, tmp_path: Path) -> None:
        assets_dir = tmp_path / "assets"
        exporter = FileAssetExporter(assets_dir=assets_dir)
        rel = exporter.export("test.png", b"\x89PNG")
        assert rel.startswith("assets/")
        assert (assets_dir / "test.png").exists() or (assets_dir / "test.png").exists()


class TestFileStorage:
    def test_saves_markdown(self, tmp_path: Path) -> None:
        storage = FileStorage(output_dir=tmp_path)
        doc = MarkdownDocument(
            source_docx=tmp_path / "source.docx",
            content="# Hello\n",
        )
        out = storage.save(doc, source_path=tmp_path / "source.docx")
        assert out.exists()
        assert "# Hello" in out.read_text(encoding="utf-8")

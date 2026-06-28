"""Tests for xlsx2md storage adapters."""

from __future__ import annotations

from pathlib import Path

from xlsx2md.domain.entities.entities import MarkdownDocument
from xlsx2md.infrastructure.storage.file_storage import FileStorage


class TestFileStorage:
    def test_saves_sheet_and_index(self, tmp_path: Path) -> None:
        storage = FileStorage(output_dir=tmp_path)
        sheet_doc = MarkdownDocument(
            source_xlsx=tmp_path / "report.xlsx",
            sheet_name="Resumen",
            content="# Resumen\n",
        )
        index_doc = MarkdownDocument(
            source_xlsx=tmp_path / "report.xlsx",
            sheet_name="_index",
            content="# Index\n",
        )

        sheet_path = storage.save(sheet_doc, source_path=tmp_path / "report.xlsx")
        index_path = storage.save(index_doc, source_path=tmp_path / "report.xlsx")

        assert sheet_path == tmp_path / "report" / "resumen.md"
        assert index_path == tmp_path / "report" / "_index.md"
        assert sheet_path.read_text(encoding="utf-8").startswith("# Resumen")

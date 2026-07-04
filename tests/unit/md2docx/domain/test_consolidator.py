"""Tests for manual consolidator."""

from __future__ import annotations

from pathlib import Path

from md2docx.domain.services.manual_consolidator import ManualConsolidator, clean_content
from md2docx.domain.value_objects.value_objects import ConversionConfig


class TestCleanContent:
    def test_removes_leading_separator(self) -> None:
        text = "---\n\n# Title\n\nBody"
        assert clean_content(text).startswith("# Title")

    def test_removes_trailing_metadata(self) -> None:
        text = "# Title\n\nBody\n\n**Fecha:** 2026"
        assert "**Fecha" not in clean_content(text)


class TestManualConsolidator:
    def test_consolidates_multiple_files(self, tmp_path: Path) -> None:
        first = tmp_path / "one.md"
        second = tmp_path / "two.md"
        first.write_text("# One\n\nFirst body", encoding="utf-8")
        second.write_text("# Two\n\nSecond body", encoding="utf-8")

        consolidator = ManualConsolidator()
        manual = consolidator.consolidate(
            [first, second],
            config=ConversionConfig(consolidate=True),
        )

        assert len(manual.sections) == 2
        assert "First body" in manual.combined
        assert "Second body" in manual.combined
        assert manual.combined.count("=" * 60) >= 4

    def test_passthrough_single_file(self, tmp_path: Path) -> None:
        md = tmp_path / "solo.md"
        md.write_text("# Solo\n\nContent", encoding="utf-8")
        manual = ManualConsolidator().consolidate(
            [md],
            config=ConversionConfig(consolidate=False),
        )
        assert manual.combined == "# Solo\n\nContent"
        assert len(manual.sections) == 1

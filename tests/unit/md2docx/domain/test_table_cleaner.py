"""Tests for table cleaner."""

from __future__ import annotations

from md2docx.domain.entities.entities import ConsolidatedManual
from md2docx.domain.services.table_cleaner import TableCleaner
from md2docx.domain.value_objects.value_objects import ConversionConfig


class TestTableCleaner:
    def test_removes_ascii_art(self) -> None:
        combined = "Intro\n\n+---+---+\n| a | b |\n+---+---+\n\n| x | y |\n|---|---|\n| 1 | 2 |"
        manual = ConsolidatedManual(combined=combined)
        result = TableCleaner().clean(manual, config=ConversionConfig())
        assert "+---" not in result.combined
        assert "| x | y |" in result.combined

    def test_adds_spacing_between_table_and_paragraph(self) -> None:
        combined = "Paragraph\n| col |\n| --- |\n| val |"
        manual = ConsolidatedManual(combined=combined)
        result = TableCleaner().clean(manual, config=ConversionConfig())
        assert "Paragraph\n\n| col |" in result.combined

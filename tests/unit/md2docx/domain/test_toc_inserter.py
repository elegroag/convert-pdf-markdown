"""Tests for TOC inserter."""

from __future__ import annotations

from md2docx.domain.entities.entities import ConsolidatedManual
from md2docx.domain.services.toc_inserter import TocInserter
from md2docx.domain.value_objects.value_objects import ConversionConfig


class TestTocInserter:
    def test_inserts_index_with_anchors(self) -> None:
        delimiter = "=" * 60
        combined = (
            f"# Manual\n\n"
            f"{delimiter}\n"
            f"Sección Uno\n"
            f"{delimiter}\n\n"
            f"Contenido uno\n\n"
            f"{delimiter}\n"
            f"Sección Dos\n"
            f"{delimiter}\n\n"
            f"Contenido dos\n"
        )
        manual = ConsolidatedManual(combined=combined)
        result = TocInserter().insert(manual, config=ConversionConfig())

        assert "# ÍNDICE DE CONTENIDOS" in result.combined
        assert "[Sección Uno](#seccion-uno)" in result.combined
        assert "[Sección Dos](#seccion-dos)" in result.combined

    def test_no_sections_returns_unchanged(self) -> None:
        manual = ConsolidatedManual(combined="# Solo\n\nTexto")
        result = TocInserter().insert(manual, config=ConversionConfig())
        assert result.combined == manual.combined

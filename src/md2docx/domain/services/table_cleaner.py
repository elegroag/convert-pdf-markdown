"""Normalize Markdown tables and remove ASCII-art blocks."""

from __future__ import annotations

from md2docx.domain.entities.entities import ConsolidatedManual
from md2docx.domain.ports.ports import ITableCleaner
from md2docx.domain.value_objects.value_objects import ConversionConfig


def _is_ascii_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("+") and "--" in stripped


def _is_markdown_table_line(line: str) -> bool:
    return line.strip().startswith("|")


class TableCleaner(ITableCleaner):
    """Remove ASCII-art tables and add spacing around Markdown tables."""

    def clean(
        self,
        manual: ConsolidatedManual,
        *,
        config: ConversionConfig | None = None,
    ) -> ConsolidatedManual:
        """Return a copy of the manual with normalized table spacing."""
        _ = config or ConversionConfig()
        lines = manual.combined.splitlines()
        cleaned_lines: list[str] = []
        prev_was_table = False
        prev_was_text = False

        for line in lines:
            if _is_ascii_table_line(line):
                continue

            is_table = _is_markdown_table_line(line)
            is_text = bool(line.strip()) and not is_table

            if is_table and prev_was_text:
                cleaned_lines.append("")
            if is_text and prev_was_table:
                cleaned_lines.append("")

            cleaned_lines.append(line)
            prev_was_table = is_table
            prev_was_text = is_text

        combined = "\n".join(cleaned_lines).strip() + "\n"
        return ConsolidatedManual(
            sections=manual.sections,
            combined=combined,
            source_path=manual.source_path,
        )


__all__ = ["TableCleaner"]

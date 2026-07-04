"""Consolidate multiple Markdown sources into a single manual."""

from __future__ import annotations

import re
from pathlib import Path

from md2docx.domain.entities.entities import ConsolidatedManual, MarkdownSection
from md2docx.domain.ports.ports import IManualConsolidator
from md2docx.domain.value_objects.value_objects import ConversionConfig

_METADATA_PREFIXES = ("**Fecha", "**Versión", "**Desarrollado")


def clean_content(text: str) -> str:
    """Remove leading separators and trailing metadata lines."""
    lines = text.splitlines()
    while lines and lines[0].strip() == "---":
        lines.pop(0)
    while lines:
        stripped = lines[-1].strip()
        if any(stripped.startswith(prefix) for prefix in _METADATA_PREFIXES):
            lines.pop()
        else:
            break
    return "\n".join(lines).strip()


class ManualConsolidator(IManualConsolidator):
    """Merge Markdown files into one consolidated manual."""

    def consolidate(
        self,
        paths: list[Path],
        *,
        config: ConversionConfig | None = None,
        titles: list[str] | None = None,
    ) -> ConsolidatedManual:
        """Combine multiple Markdown files with section delimiters."""
        cfg = config or ConversionConfig()
        if len(paths) == 1 and not cfg.consolidate:
            content = paths[0].read_text(encoding="utf-8")
            cleaned = clean_content(content)
            section = MarkdownSection(source=paths[0], title=paths[0].stem, content=cleaned)
            return ConsolidatedManual(
                sections=[section],
                combined=cleaned,
                source_path=paths[0],
            )

        sections: list[MarkdownSection] = []
        chunks: list[str] = []
        delimiter = cfg.section_delimiter

        for idx, path in enumerate(paths):
            raw = path.read_text(encoding="utf-8")
            cleaned = clean_content(raw)
            title = titles[idx] if titles and idx < len(titles) else path.stem
            section = MarkdownSection(source=path, title=title, content=cleaned)
            sections.append(section)
            chunks.append(f"{delimiter}\n{title}\n{delimiter}\n\n{cleaned}")

        combined = "\n\n".join(chunks).strip() + "\n"
        return ConsolidatedManual(
            sections=sections,
            combined=combined,
            source_path=paths[0] if paths else None,
        )

    def passthrough(self, path: Path) -> ConsolidatedManual:
        """Wrap a single Markdown file without multi-file consolidation."""
        content = path.read_text(encoding="utf-8")
        cleaned = clean_content(content)
        section = MarkdownSection(source=path, title=path.stem, content=cleaned)
        return ConsolidatedManual(
            sections=[section],
            combined=cleaned,
            source_path=path,
        )


def section_title_from_content(content: str, delimiter: str) -> str | None:
    """Extract the first section title delimited by ``delimiter`` lines."""
    pattern = re.escape(delimiter) + r"\n(.+?)\n" + re.escape(delimiter)
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else None


__all__ = ["ManualConsolidator", "clean_content", "section_title_from_content"]

"""Insert a table of contents into consolidated Markdown."""

from __future__ import annotations

import re

from md2docx.domain.entities.entities import ConsolidatedManual
from md2docx.domain.ports.ports import ITocInserter
from md2docx.domain.services.anchor_slug import AnchorSlug
from md2docx.domain.value_objects.value_objects import ConversionConfig


class TocInserter(ITocInserter):
    """Build and insert a Markdown table of contents."""

    def insert(
        self,
        manual: ConsolidatedManual,
        *,
        config: ConversionConfig | None = None,
    ) -> ConsolidatedManual:
        """Insert ``# ÍNDICE DE CONTENIDOS`` after the main title."""
        cfg = config or ConversionConfig()
        delimiter = re.escape(cfg.section_delimiter)
        pattern = re.compile(delimiter + r"\n(.+?)\n" + delimiter, re.DOTALL)

        sections = pattern.findall(manual.combined)
        if not sections:
            return manual

        toc_lines = ["# ÍNDICE DE CONTENIDOS", ""]
        for title in sections:
            anchor = AnchorSlug.slugify(title)
            toc_lines.append(f"- [{title}](#{anchor})")
        toc_block = "\n".join(toc_lines)

        lines = manual.combined.splitlines()
        insert_at = 0
        for idx, line in enumerate(lines):
            if line.strip().startswith("#"):
                insert_at = idx + 1
                break

        new_lines = lines[:insert_at] + ["", toc_block, ""] + lines[insert_at:]
        combined = "\n".join(new_lines).strip() + "\n"
        return ConsolidatedManual(
            sections=manual.sections,
            combined=combined,
            source_path=manual.source_path,
        )


__all__ = ["TocInserter"]

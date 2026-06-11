"""HTML renderer (optional output)."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Iterable

from pdf2md.domain.entities.entities import (
    MarkdownDocument,
    MarkdownPage,
    PdfDocument,
)
from pdf2md.domain.ports.ports import IRenderer
from pdf2md.domain.value_objects.value_objects import ConversionConfig
from pdf2md.infrastructure.renderers.markdown_renderer import MarkdownRenderer


class HtmlRenderer(IRenderer):
    """Render a PDF document as standalone HTML.

    Internally uses the :class:`MarkdownRenderer` and wraps the
    resulting Markdown in a minimal HTML document. A full Markdown
    → HTML converter is intentionally not bundled to keep the
    dependency surface small; this renderer produces readable HTML
    from the same block model used by the Markdown renderer.
    """

    def __init__(self, config: ConversionConfig | None = None) -> None:
        self._config = config or ConversionConfig()
        self._md = MarkdownRenderer(self._config)

    def render(self, document: PdfDocument) -> MarkdownDocument:
        """Render the PDF document to HTML, packaged as a ``MarkdownDocument``."""
        md = self._md.render(document)
        body = "\n".join(
            self._html_for_page(page) for page in md.pages
        )
        html_doc = (
            "<!DOCTYPE html>\n"
            "<html><head><meta charset=\"utf-8\"><title>"
            f"{html.escape(document.metadata.title or document.file_path.name)}"
            "</title></head><body>\n"
            f"{body}\n"
            "</body></html>"
        )
        page = MarkdownPage(page_number=1, content=html_doc)
        return MarkdownDocument(
            source_pdf=document.file_path,
            pages=[page],
            assets_dir=md.assets_dir,
            frontmatter="",
        )

    def _html_for_page(self, page: MarkdownPage) -> str:
        """Convert a Markdown page body to a best-effort HTML fragment."""
        lines: list[str] = []
        for raw_line in page.content.splitlines():
            line = raw_line.rstrip()
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                text = line[level:].strip()
                lines.append(f"<h{level}>{html.escape(text)}</h{level}>")
            elif line.startswith(self._config.code_fence):
                lines.append(line)  # keep fences verbatim
            elif line.startswith("![") and "](" in line and line.endswith(")"):
                alt_start = line.index("![") + 2
                alt_end = line.index("](")
                src_start = alt_end + 2
                src_end = line.rindex(")")
                alt = html.escape(line[alt_start:alt_end])
                src = html.escape(line[src_start:src_end])
                lines.append(f'<img alt="{alt}" src="{src}">')
            else:
                lines.append(f"<p>{html.escape(line)}</p>")
        return "\n".join(lines)


__all__ = ["HtmlRenderer"]

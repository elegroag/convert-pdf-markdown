"""Markdown renderer for DOCX document blocks."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from docx2md.domain.entities.entities import (
    DocumentBlock,
    HeadingBlock,
    HorizontalRuleBlock,
    ImageBlock,
    ListItemBlock,
    MarkdownDocument,
    ParagraphBlock,
    TableBlock,
)
from docx2md.domain.exceptions import RenderingError
from docx2md.domain.ports.ports import IMarkdownRenderer
from docx2md.domain.value_objects.value_objects import ConversionConfig


class MarkdownRenderer(IMarkdownRenderer):
    """Convert document blocks to Markdown."""

    def __init__(self, config: ConversionConfig | None = None) -> None:
        self._config = config or ConversionConfig()

    def render(self, blocks: Sequence[DocumentBlock]) -> MarkdownDocument:
        """Render blocks into a :class:`MarkdownDocument`."""
        try:
            lines: list[str] = []
            prev: DocumentBlock | None = None
            for block in blocks:
                chunk = self._render_block(block, prev)
                if chunk:
                    lines.append(chunk)
                prev = block
            content = "\n".join(lines) + "\n" if lines else ""
            return MarkdownDocument(source_docx=Path("."), content=content)
        except RenderingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RenderingError(f"failed to render blocks: {exc}") from exc

    def _render_block(self, block: DocumentBlock, prev: DocumentBlock | None) -> str:
        if isinstance(block, HeadingBlock):
            return self._render_heading(block, prev)
        if isinstance(block, ParagraphBlock):
            return self._render_paragraph(block, prev)
        if isinstance(block, ImageBlock):
            return self._render_image(block, prev)
        if isinstance(block, TableBlock):
            return self._render_table(block, prev)
        if isinstance(block, ListItemBlock):
            return self._render_list_item(block, prev)
        if isinstance(block, HorizontalRuleBlock):
            return "\n---\n"
        return ""

    def _render_heading(self, block: HeadingBlock, prev: DocumentBlock | None) -> str:
        prefix = "\n" if prev is not None else ""
        hashes = "#" * min(block.level, 6)
        return f"{prefix}{hashes} {block.text}\n"

    def _render_paragraph(self, block: ParagraphBlock, prev: DocumentBlock | None) -> str:
        return f"\n{block.text}\n"

    def _render_image(self, block: ImageBlock, prev: DocumentBlock | None) -> str:
        alt = block.alt_text or "image"
        return f"\n![{alt}]({block.filename})\n"

    def _render_table(self, block: TableBlock, prev: DocumentBlock | None) -> str:
        if not block.rows:
            return ""
        lines: list[str] = ["\n"]
        header = block.rows[0]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join("---" for _ in header) + " |")
        for row in block.rows[1:]:
            normalized = list(row) + [""] * (len(header) - len(row))
            lines.append("| " + " | ".join(normalized[: len(header)]) + " |")
        lines.append("")
        return "\n".join(lines)

    def _render_list_item(self, block: ListItemBlock, prev: DocumentBlock | None) -> str:
        indent = "  " * block.level
        marker = "1." if block.ordered else "-"
        prefix = "\n" if prev is not None and not isinstance(prev, ListItemBlock) else ""
        return f"{prefix}{indent}{marker} {block.text}"


__all__ = ["MarkdownRenderer"]

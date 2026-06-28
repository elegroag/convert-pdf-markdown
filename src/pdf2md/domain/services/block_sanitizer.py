"""BlockSanitizer — demotes misclassified headings back to paragraphs."""

from __future__ import annotations

import re

from pdf2md.domain.value_objects.enums import BlockType
from pdf2md.domain.value_objects.value_objects import ContentBlock

_TOC_DOTS_RE = re.compile(r"\.{4,}")


class BlockSanitizer:
    """Stateless namespace for cleaning mis-tagged content blocks."""

    @classmethod
    def demote_false_headings(cls, blocks: list[ContentBlock]) -> list[ContentBlock]:
        """Convert headings that cannot be real titles back to paragraphs."""
        return [cls._maybe_demote(b) for b in blocks]

    @classmethod
    def _maybe_demote(cls, block: ContentBlock) -> ContentBlock:
        if block.block_type != BlockType.HEADING.value:
            return block
        stripped = block.text.strip()
        if not stripped:
            return block
        if stripped[0].islower():
            return cls._as_paragraph(block)
        if _TOC_DOTS_RE.search(stripped):
            return cls._as_paragraph(block)
        return block

    @staticmethod
    def _as_paragraph(block: ContentBlock) -> ContentBlock:
        return ContentBlock(
            block_type=BlockType.PARAGRAPH.value,
            text=block.text,
            level=0,
            font_size=block.font_size,
            is_bold=block.is_bold,
            bbox=block.bbox,
        )


__all__ = ["BlockSanitizer"]

"""Stable keys for content blocks based on page position."""

from __future__ import annotations

from pdf2md.domain.value_objects.value_objects import ContentBlock


def block_position_key(page_number: int, block: ContentBlock) -> str:
    """Return a stable key for ``block`` using page number and Y position.

    Text alone is ambiguous when headings repeat; position disambiguates.
    """
    text = block.text.strip()
    if block.bbox:
        y0 = int(round(block.bbox[1] * 10))
        x0 = int(round(block.bbox[0] * 10))
        return f"{page_number}:{y0}:{x0}:{text}"
    return f"{page_number}::{text}"


__all__ = ["block_position_key"]

"""Merge page elements into natural reading order."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pdf2md.domain.entities.entities import ImageAsset, PdfPage, TableNode
from pdf2md.domain.value_objects.value_objects import ContentBlock, Link


ChunkKind = Literal["text", "table", "image", "link_list"]


@dataclass(frozen=True)
class PageChunk:
    """A renderable unit positioned on a PDF page."""

    kind: ChunkKind
    y0: float
    x0: float
    block: ContentBlock | None = None
    table: TableNode | None = None
    image: ImageAsset | None = None
    links: tuple[Link, ...] = ()


def _position(
    bbox: tuple[float, float, float, float] | None,
) -> tuple[float, float]:
    if not bbox:
        return (0.0, 0.0)
    return (bbox[1], bbox[0])


def build_reading_order(page: PdfPage) -> list[PageChunk]:
    """Interleave text blocks, tables, and images by vertical position."""
    chunks: list[PageChunk] = []
    for block in page.blocks:
        y0, x0 = _position(block.bbox)
        chunks.append(PageChunk(kind="text", y0=y0, x0=x0, block=block))
    for table in page.tables:
        y0, x0 = _position(table.bbox)
        chunks.append(PageChunk(kind="table", y0=y0, x0=x0, table=table))
    for image in page.images:
        y0, x0 = _position(image.bbox)
        chunks.append(PageChunk(kind="image", y0=y0, x0=x0, image=image))
    chunks.sort(key=lambda c: (c.y0, c.x0))
    return chunks


__all__ = ["PageChunk", "build_reading_order"]

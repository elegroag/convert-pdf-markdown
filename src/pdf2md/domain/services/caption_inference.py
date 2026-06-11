"""Caption inference: locate figure/table captions near an image asset.

v0.2.0 feature. The PyMuPDF extractor only knows about images by their
bounding box; the figure number and caption text live in nearby text
blocks. This helper scans the page's text blocks and assigns a
human-readable caption to each :class:`ImageAsset` when possible.

Heuristic:
- For each image, look at text blocks on the same page.
- A caption is a text block that starts with one of the patterns:
  ``Figure N.M``, ``Figura N.M``, ``Table N.M``, ``Tabla N.M``,
  ``Listing N.M``, ``Image N.M`` (case-insensitive, with optional
  punctuation).
- The text block is "near" the image when:
  - its y-coordinate is within ±40 pt of the image's y-range, AND
  - its x-coordinate starts near the image's x (within ±60 pt).
- When multiple matches exist, the closest one wins.
- When no match exists, the caption is left as ``None`` and the renderer
  falls back to its default ``Figure {index}`` placeholder.
"""

from __future__ import annotations

import re
from typing import Iterable

from pdf2md.domain.entities.entities import ImageAsset, ContentBlock

# Patterns that start a caption. English and Spanish, with flexible
# separators (space, hyphen, en-dash, em-dash).
_CAPTION_RE = re.compile(
    r"^\s*(figure|figura|table|tabla|listing|imagen|image)\s*"
    r"\d+(?:\.\d+)?\s*[:\-–—]?\s*(.*)$",
    re.IGNORECASE,
)

_Y_TOLERANCE = 40.0  # pt
_X_TOLERANCE = 60.0  # pt


def _bbox_y_range(bbox: tuple[float, float, float, float] | None) -> tuple[float, float]:
    if not bbox:
        return (0.0, 0.0)
    return (bbox[1], bbox[3])


def _bbox_x0(bbox: tuple[float, float, float, float] | None) -> float:
    if not bbox:
        return 0.0
    return bbox[0]


def _caption_distance(image_bbox, block_bbox) -> float:
    """Lower is closer. ``inf`` when the block is not near the image."""
    iy0, iy1 = _bbox_y_range(image_bbox)
    by0, by1 = _bbox_y_range(block_bbox)
    if iy0 == 0.0 and iy1 == 0.0:
        return float("inf")
    # Y-axis: any overlap or proximity is fine; below is preferred.
    y_dist = 0.0
    if by1 < iy0:
        y_dist = iy0 - by1
    elif by0 > iy1:
        y_dist = by0 - iy1
    # X-axis: blocks far to the right are unlikely captions.
    ix0 = _bbox_x0(image_bbox)
    bx0 = _bbox_x0(block_bbox)
    x_dist = max(0.0, abs(bx0 - ix0) - _X_TOLERANCE)
    return y_dist + x_dist


def _parse_caption(text: str) -> str | None:
    """Extract a caption from a block of text, or ``None``."""
    if not text:
        return None
    # Find the first caption-like line and consume it.
    for line in text.splitlines():
        line = line.strip()
        m = _CAPTION_RE.match(line)
        if m:
            label = m.group(1).capitalize()
            number_match = re.search(r"\d+(?:\.\d+)?", m.group(0))
            if number_match:
                number = number_match.group(0)
                return f"{label} {number}: {m.group(2).strip()}".rstrip(": ")
    return None


def _nearest_caption(
    image_bbox, text_blocks: Iterable[ContentBlock]
) -> str | None:
    best: tuple[float, str] | None = None
    for block in text_blocks:
        if not block.bbox:
            continue
        cap = _parse_caption(block.text)
        if not cap:
            continue
        d = _caption_distance(image_bbox, block.bbox)
        if d > _Y_TOLERANCE + _X_TOLERANCE:
            continue
        if best is None or d < best[0]:
            best = (d, cap)
    return best[1] if best else None


def infer_captions(
    images: list[ImageAsset],
    text_blocks: Iterable[ContentBlock],
) -> None:
    """Populate ``image.caption`` in place for each image.

    Images whose caption is already non-empty are left untouched. Images
    with no nearby caption are left with ``caption=None`` so the
    renderer applies its fallback.
    """
    blocks = list(text_blocks)
    for image in images:
        if image.caption:
            continue
        cap = _nearest_caption(image.bbox, blocks)
        if cap:
            image.caption = cap


__all__ = ["infer_captions"]

"""Apply inline Markdown links to paragraph text."""

from __future__ import annotations

import re

from pdf2md.domain.value_objects.value_objects import ContentBlock, Link


def _overlaps(
    link_bbox: tuple[float, float, float, float] | None,
    block_bbox: tuple[float, float, float, float] | None,
) -> bool:
    if not link_bbox or not block_bbox:
        return True
    lx0, ly0, lx1, ly1 = link_bbox
    bx0, by0, bx1, by1 = block_bbox
    if lx0 == 0.0 and ly0 == 0.0 and lx1 == 0.0 and ly1 == 0.0:
        return True
    if bx0 == 0.0 and by0 == 0.0 and bx1 == 0.0 and by1 == 0.0:
        return True
    return lx0 < bx1 and lx1 > bx0 and ly0 < by1 and ly1 > by0


def apply_inline_links(
    text: str,
    links: list[Link],
    *,
    block: ContentBlock | None = None,
) -> str:
    """Replace link text with ``[text](url)`` when it appears in ``text``."""
    if not text or not links:
        return text

    block_bbox = block.bbox if block else None
    applicable = [
        link
        for link in links
        if not link.is_internal and link.url and _overlaps(link.bbox, block_bbox)
    ]
    applicable.sort(key=lambda link: len(link.text or ""), reverse=True)

    for link in applicable:
        label = (link.text or link.url).strip()
        if not label or len(label) < 3:
            continue
        replacement = f"[{label}]({link.url})"
        if replacement in text:
            continue
        if " " in label:
            if label not in text:
                continue
            text = text.replace(label, replacement, 1)
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(label)}(?!\w)")
        if not pattern.search(text):
            continue
        text = pattern.sub(replacement, text, count=1)
    return text


__all__ = ["apply_inline_links"]

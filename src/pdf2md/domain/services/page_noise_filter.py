"""PageNoiseFilter — removes recurring headers, footers, and page numbers."""

from __future__ import annotations

import re

from pdf2md.domain.value_objects.value_objects import ContentBlock

_FOOTER_RE = re.compile(
    r"contraloria\.gov\.co|Carrera 69 No\.\s*44-35",
    re.IGNORECASE,
)
_PAGE_NUM_ONLY_RE = re.compile(r"^\d{1,3}$")
_ELABORO_RE = re.compile(r"^\d{1,3}\s+Elaboró:", re.IGNORECASE)
_PAGE_OF_RE = re.compile(r"^\s*(?:page|página|pag\.?)\s+\d+\s*(?:of|de|/)\s*\d+\s*$", re.IGNORECASE)
_SHORT_HEADER_RE = re.compile(r"^\s*(?:chapter|capítulo|section|sección)\s+\d+\s*$", re.IGNORECASE)


class PageNoiseFilter:
    """Stateless namespace for stripping page-level noise blocks."""

    @classmethod
    def filter(cls, blocks: list[ContentBlock]) -> list[ContentBlock]:
        """Return blocks with institutional footers and page numbers removed."""
        return [b for b in blocks if not cls._is_noise(b)]

    @staticmethod
    def _is_noise(block: ContentBlock) -> bool:
        text = block.text.strip()
        if not text:
            return True
        if _FOOTER_RE.search(text):
            return True
        if _PAGE_NUM_ONLY_RE.match(text):
            return True
        if _ELABORO_RE.match(text):
            return True
        if _PAGE_OF_RE.match(text):
            return True
        if block.bbox:
            _, y0, _, y1 = block.bbox
            if _SHORT_HEADER_RE.match(text) and (y1 <= 72 or y0 >= 720):
                return True
            if y1 <= 72 and len(text.split()) <= 6:
                return True
            if y0 >= 720 and len(text.split()) <= 8:
                return True
        return False


__all__ = ["PageNoiseFilter"]

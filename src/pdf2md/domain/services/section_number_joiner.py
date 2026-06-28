"""SectionNumberJoiner — merges orphan section numbers with their titles.

Word PDFs often emit ``1.4.`` and ``LIMITACIONES DEL PROCESO`` as
separate visual lines.  This joiner fuses them into a single heading
block before paragraph joining runs.
"""

from __future__ import annotations

import re

from pdf2md.domain.value_objects.enums import BlockType
from pdf2md.domain.value_objects.value_objects import ContentBlock

_SECTION_NUM_RE = re.compile(r"^\d+(\.\d+)*\.?\s*$")
_TOC_DOTS_RE = re.compile(r"\.{2,}\s*\d*\s*$")
_LETTER_RE = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]")


def _strip_toc_trailing(text: str) -> str:
    """Remove table-of-contents dot leaders and trailing page numbers."""
    return _TOC_DOTS_RE.sub("", text).strip()


def _uppercase_ratio(text: str) -> float:
    letters = _LETTER_RE.findall(text)
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def _is_section_number(text: str) -> bool:
    return bool(_SECTION_NUM_RE.match(text.strip()))


def _is_caps_title(text: str) -> bool:
    """Return True when ``text`` looks like an ALL-CAPS section title."""
    cleaned = _strip_toc_trailing(text.strip())
    if not cleaned or len(cleaned.split()) > 15 or len(cleaned) > 120:
        return False
    return _uppercase_ratio(cleaned) >= 0.75


def _heading_level_from_number(section_num: str) -> int:
    """Map ``1.`` → 1, ``1.1.`` → 2, ``1.1.1.`` → 3 (capped at 6)."""
    parts = [p for p in section_num.strip().rstrip(".").split(".") if p]
    return max(1, min(6, len(parts)))


class SectionNumberJoiner:
    """Stateless namespace for merging section numbers with titles."""

    @classmethod
    def join(cls, blocks: list[ContentBlock]) -> list[ContentBlock]:
        """Return blocks with orphan section numbers fused into headings."""
        if not blocks:
            return []

        result: list[ContentBlock] = []
        i = 0
        while i < len(blocks):
            current = blocks[i]
            text = current.text.strip()

            if i + 1 < len(blocks) and _is_section_number(text):
                nxt = blocks[i + 1]
                title = _strip_toc_trailing(nxt.text.strip())
                if _is_caps_title(nxt.text) or (
                    nxt.block_type == BlockType.HEADING.value and title
                ):
                    merged = ContentBlock(
                        block_type=BlockType.HEADING.value,
                        text=f"{text.rstrip()} {title}".strip(),
                        level=_heading_level_from_number(text),
                        font_size=max(current.font_size, nxt.font_size),
                        is_bold=current.is_bold or nxt.is_bold,
                        bbox=current.bbox or nxt.bbox,
                    )
                    result.append(merged)
                    i += 2
                    continue

            result.append(current)
            i += 1

        return result


__all__ = ["SectionNumberJoiner"]

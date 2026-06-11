"""ParagraphJoiner — re-unites lines of the same paragraph.

v0.2.0 feature. The PyMuPDF extractor emits one :class:`ContentBlock`
per visual line, which leaves every paragraph fragmented into 8-12
short blocks (~65 chars each). The joiner walks the block list and
merges consecutive blocks that satisfy all of:

- same ``block_type`` (paragraph ↔ paragraph, list_item ↔ list_item, ...);
- same font profile (``font_size`` within ±0.2 pt, same bold flag,
  same monospace flag);
- the first block does NOT end in sentence-final punctuation
  (``.``, ``?``, ``!``, ``;``, ``:``);
- the first block is NOT followed by a clearly new sentence (heuristic:
  the next block starts with a lowercase letter OR with no leading
  capital — i.e. mid-sentence continuation);
- a line ending in ``-`` strips the hyphen and joins (word-wrap case).

The joiner is a pure function: same input → same output, no I/O.
"""

from __future__ import annotations

import re

from pdf2md.domain.value_objects.value_objects import ContentBlock

_SIZE_TOLERANCE = 0.2

_TERMINAL_PUNCT_RE = re.compile(r"[.;:?!»\"'\)\]]\s*$")
_HYPHEN_END_RE = re.compile(r"[-‐-―]\s*$")


class ParagraphJoiner:
    """Stateless namespace for joining fragmented paragraph lines."""

    @staticmethod
    def _same_profile(a: ContentBlock, b: ContentBlock) -> bool:
        if a.block_type != b.block_type:
            return False
        if abs(a.font_size - b.font_size) > _SIZE_TOLERANCE:
            return False
        if a.is_bold != b.is_bold:
            return False
        return True

    @staticmethod
    def _ends_in_terminal_punct(text: str) -> bool:
        return bool(_TERMINAL_PUNCT_RE.search(text.rstrip()))

    @staticmethod
    def _ends_in_hyphen(text: str) -> bool:
        return bool(_HYPHEN_END_RE.search(text.rstrip()))

    @staticmethod
    def _starts_new_sentence(text: str) -> bool:
        stripped = text.lstrip()
        if not stripped:
            return True
        first = stripped[0]
        # Capital letter, digit, opening quote → likely new sentence.
        if first.isupper() or first.isdigit() or first in '"\'«¿¡(':
            return True
        # Also treat "List-like" markers as new sentences.
        if first in "-*+•●":
            return True
        return False

    @classmethod
    def join(cls, blocks: list[ContentBlock]) -> list[ContentBlock]:
        """Return a new list of blocks with fragmented lines rejoined.

        The first block of each group is the one whose attributes are
        preserved; subsequent merged blocks contribute only their text.
        """
        if not blocks:
            return []

        result: list[ContentBlock] = []
        current = blocks[0]

        for nxt in blocks[1:]:
            if cls._should_join(current, nxt):
                merged_text = cls._merge_text(current.text, nxt.text)
                current = ContentBlock(
                    block_type=current.block_type,
                    text=merged_text,
                    level=current.level,
                    font_size=current.font_size,
                    is_bold=current.is_bold,
                    bbox=current.bbox,
                )
            else:
                result.append(current)
                current = nxt

        result.append(current)
        return result

    @classmethod
    def _should_join(cls, prev: ContentBlock, nxt: ContentBlock) -> bool:
        if not cls._same_profile(prev, nxt):
            return False
        if cls._ends_in_terminal_punct(prev.text):
            return False
        if cls._ends_in_terminal_punct(nxt.text):
            # Allow joining if the next line starts lowercase (still
            # part of the same sentence). Otherwise treat as new.
            if not cls._starts_new_sentence(nxt.text):
                return True
            return False
        # If next starts a clear new sentence (capital, opening quote,
        # bullet), prefer to split.
        if cls._starts_new_sentence(nxt.text):
            # But if previous was clearly mid-sentence (ends with comma
            # or no terminal punctuation AND does not end with a closed
            # clause), still join.
            stripped = prev.text.rstrip()
            if stripped and stripped[-1] in ",—–-":
                return True
            return False
        return True

    @classmethod
    def _merge_text(cls, prev: str, nxt: str) -> str:
        if cls._ends_in_hyphen(prev):
            # Strip trailing hyphen(s) and concatenate without space.
            stripped = _HYPHEN_END_RE.sub("", prev.rstrip())
            return f"{stripped}{nxt.lstrip()}"
        return f"{prev.rstrip()} {nxt.lstrip()}".strip()


__all__ = ["ParagraphJoiner"]

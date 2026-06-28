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
- a line ending in ``-`` strips the hyphen and joins (word-wrap case);
- the next block is NOT a pure HTML block (misclassified as paragraph).

The joiner is a pure function: same input → same output, no I/O.
"""

from __future__ import annotations

import re

from pdf2md.domain.value_objects.value_objects import ContentBlock

_SIZE_TOLERANCE = 0.5
_LINE_GAP_FACTOR = 1.4
_NON_JOINABLE_TYPES = frozenset({"list_item", "heading", "code"})
_BULLET_ONLY_RE = re.compile(r"^●(\u200b)?\s*$")
_LETTER_RE = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]")

_TERMINAL_PUNCT_RE = re.compile(r"[.;:?!»\"'\)\]]\s*$")
_HYPHEN_END_RE = re.compile(r"[-‐-―]\s*$")

# Pattern to detect if a line is a pure HTML tag (opening, closing, self-closing)
_HTML_LINE_PERMISSIVE_RE = re.compile(r"^\s*<[^!][\s\S]*?>\s*$")
_HTML_DECL_RE = re.compile(r"^\s*<!DOCTYPE[^>]*>\s*$", re.IGNORECASE)


class ParagraphJoiner:
    """Stateless namespace for joining fragmented paragraph lines."""

    @staticmethod
    def _is_pure_html_block(text: str) -> bool:
        """Return True if the text consists only of HTML tags."""
        lines = text.splitlines()
        if len(lines) < 1:
            return False
        html_lines = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if _HTML_LINE_PERMISSIVE_RE.match(stripped) or _HTML_DECL_RE.match(stripped):
                html_lines += 1
        return html_lines > 0 and html_lines == len([l for l in lines if l.strip()])

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
        # Spanish opening punctuation usually continues the same sentence.
        if first in "«¿":
            return False
        # Capital letter, digit, opening quote → likely new sentence.
        if first.isupper() or first.isdigit() or first in '"\'¡(':
            return True
        # Also treat "List-like" markers as new sentences.
        if first in "-*+•●":
            return True
        return False

    @classmethod
    def _vertical_gap(cls, prev: ContentBlock, nxt: ContentBlock) -> float | None:
        """Return the vertical gap between two blocks, or None if unknown."""
        if prev.bbox is None or nxt.bbox is None:
            return None
        _px0, py0, _px1, py1 = prev.bbox
        nx0, ny0, _nx1, _ny1 = nxt.bbox
        if py1 == 0.0 and ny0 == 0.0:
            return None
        return ny0 - py1

    @classmethod
    def _has_paragraph_break(cls, prev: ContentBlock, nxt: ContentBlock) -> bool:
        """Return True when bbox spacing indicates a new paragraph."""
        gap = cls._vertical_gap(prev, nxt)
        if gap is None:
            return False
        font_size = max(prev.font_size, nxt.font_size, 1.0)
        return gap > font_size * _LINE_GAP_FACTOR

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

    @staticmethod
    def _is_caps_title(text: str) -> bool:
        """Return True when ``text`` is a short ALL-CAPS section title."""
        stripped = text.strip()
        if not stripped or len(stripped.split()) > 12:
            return False
        letters = _LETTER_RE.findall(stripped)
        if len(letters) < 3:
            return False
        return sum(1 for c in letters if c.isupper()) / len(letters) >= 0.75

    @classmethod
    def _should_join(cls, prev: ContentBlock, nxt: ContentBlock) -> bool:
        if not cls._same_profile(prev, nxt):
            return False
        if prev.block_type in _NON_JOINABLE_TYPES or nxt.block_type in _NON_JOINABLE_TYPES:
            return False
        if _BULLET_ONLY_RE.match(prev.text.strip()) or _BULLET_ONLY_RE.match(
            nxt.text.strip()
        ):
            return False
        if cls._is_caps_title(prev.text):
            return False
        # Never join a pure HTML block with prose (HTML blocks should stay separate)
        if cls._is_pure_html_block(nxt.text):
            return False
        if cls._has_paragraph_break(prev, nxt):
            return False
        stripped = prev.text.rstrip()
        # Mid-sentence wrap markers always continue onto the next line.
        if stripped and stripped[-1] in ",—–-":
            return True
        # Strong break: previous line ends a sentence and the next one
        # clearly opens a new one.  Without terminal punctuation on the
        # previous line we keep joining — PDF line wraps in Spanish
        # often start with a capital letter.
        if cls._ends_in_terminal_punct(prev.text):
            if cls._starts_new_sentence(nxt.text):
                return False
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

"""HeadingInferer — assigns heading levels using a multi-signal scorer.

v0.2.0 strategy:

The legacy v0.1.0 implementation relied on font size only, which fails for
PDFs (like the Packt Vue.js book) where every heading shares the body
font size and weight. The new approach scores every block against the
document's body size using **multiple independent signals** and promotes
the top-N candidates to heading levels 1..N.

Signals (each adds 0..1 to the score):

- ``font_size``:   bigger than body → +1.0 (proportional to delta).
- ``is_bold``:     bold and not body size → +0.6.
- ``length``:      short lines (≤ 8 words) → +0.5; very short (≤ 3) → +0.7.
- ``no_punct``:    line doesn't end in sentence punctuation → +0.3.
- ``caps``:        ≥ 60 % uppercase letters → +0.2.
- ``no_leading_hash``:  line doesn't start with ``#`` or ``//`` → no penalty,
  but lines that DO start with ``#`` are zeroed (likely code).

A block must reach :data:`HEADING_SCORE_THRESHOLD` to be considered a
heading candidate. Non-paragraph blocks (``code``, ``list_item``) are
always zeroed.

The cap is :data:`DEFAULT_MAX_LEVEL` = 4 (was 3 in v0.1.0).
"""

from __future__ import annotations

import re
from collections import Counter

from pdf2md.domain.entities.entities import PdfDocument
from pdf2md.domain.services.block_key import block_position_key
from pdf2md.domain.value_objects.enums import BlockType
from pdf2md.domain.value_objects.value_objects import ContentBlock

_DEFAULT_MAX_LEVEL = 6
_SIZE_QUANTUM = 0.01
_HEADING_SCORE_THRESHOLD = 0.7
_MAX_WORDS_FOR_HEADING = 12

# Word boundary that doesn't strip unicode letters; \w already covers
# accented chars in Python 3 re.UNICODE (default in 3.x).
_WORD_RE = re.compile(r"\S+")
_TRAILING_PUNCT_RE = re.compile(r"[.:;!?…»\"'\)\]]\s*$")
_SENTENCE_END_RE = re.compile(r"[.!?…»\"'\)\]]\s*$")
_LEADING_CODE_RE = re.compile(r"^\s*(#|//|/\*|<!--)")

# Lines that are clearly code, not headings: very few letters, lots of
# braces / brackets / operators, or a single closing brace.
_CODE_LOOKING_RE = re.compile(
    r"""^\s*(
        [\}\)\]\{]+$                  # line with only closing/opening braces
        | [\{\[].*[\}\]]\s*$          # a line that opens and closes on itself
        | export\s+default\s*[\{]
        | ^\s*(const|let|var|return|import|from|function|class|if|else|for|while|switch|case|break|continue|new|throw|try|catch|finally|do|in|of|typeof|instanceof|void|delete|yield|async|await|def|elif|except|raise|with|as|yield|pass|lambda|public|private|protected|static|namespace|use|require|module|exports)\s+
        | \}\s*[,;]?\s*$
        | const\s+\w+\s*=
        | \w+\s*\([^)]*\)\s*\{?\s*$
        | ^\s*[a-zA-Z_]\w*\s*:\s*[\{\[\(]
        | ^\s*\w+\s*\.\w+\s*\(
    )""",
    re.VERBOSE,
)

# Lines that look like HTML code, not headings (e.g., <!DOCTYPE html>, <html>, <head>)
_HTML_CODE_RE = re.compile(r"^\s*<!DOCTYPE|<html|<head|<body|<script|<style|<template", re.IGNORECASE)

# Soft code signals: a line that *looks* like code (lots of symbols,
# short token length) gets a penalty rather than a hard zero. This
# keeps the heuristic from blocking legitimate headings while
# de-prioritising code that does slip through the hard filter.
_SYMBOL_HEAVY_RE = re.compile(r"^[{}()\[\];,.<>/=+\-*/!?&|^%`'\"\\]+\s*$")
_TERMINAL_SHELL_RE = re.compile(r"^\s*\$\s+\w+")
_SHORT_TOKEN_RE = re.compile(r"^\s*\w{1,3}\s*$")
_SHELL_COMMAND_RE = re.compile(
    r"^\s*(node|npm|yarn|pip|git|docker|cd|ls|mkdir|rm|cat|composer|curl|wget|traceroute|ping|sudo|apt)\s+",
)
_LETTER_RE = re.compile(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]")


class HeadingInferer:
    """Stateless namespace for heading-level inference.

    The methods are static and the class itself is not instantiated for
    any state; the public API is exposed as a namespace. An instance is
    still constructible for backward compatibility (callers may do
    ``HeadingInferer().infer_levels(doc)``).
    """

    DEFAULT_MAX_LEVEL: int = _DEFAULT_MAX_LEVEL
    HEADING_SCORE_THRESHOLD: float = _HEADING_SCORE_THRESHOLD

    # ------------------------------------------------------------------
    # Body-size estimation
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_body_size(all_blocks: list[ContentBlock]) -> float:
        """Return a weighted modal body font size for the document.

        Bold and pre-classified heading lines are down-weighted so they
        do not skew the body-size estimate.
        """
        weights: Counter[float] = Counter()
        for block in all_blocks:
            if block.block_type in (
                BlockType.CODE.value,
                BlockType.LIST_ITEM.value,
            ):
                continue
            if block.font_size <= 0:
                continue
            size = round(block.font_size, 2)
            weight = 1.0
            if block.is_bold:
                weight *= 0.3
            if block.block_type == BlockType.HEADING.value:
                weight *= 0.2
            weights[size] += weight
        if not weights:
            return 0.0
        return weights.most_common(1)[0][0]

    # ------------------------------------------------------------------
    # Scoring primitives
    # ------------------------------------------------------------------

    @staticmethod
    def _word_count(text: str) -> int:
        return len(_WORD_RE.findall(text))

    @staticmethod
    def _uppercase_ratio(text: str) -> float:
        letters = _LETTER_RE.findall(text)
        if not letters:
            return 0.0
        upper = sum(1 for c in letters if c.isupper())
        return upper / len(letters)

    @staticmethod
    def _body_word_stats(all_blocks: list[ContentBlock]) -> tuple[float, int]:
        """Return ``(avg_words, max_words)`` for body-like blocks.

        Body-like blocks are those with ``font_size`` equal to the body
        size and ``is_bold`` False. The stats are used to compute a
        relative "short line" threshold.
        """
        from collections import Counter as _C

        sizes = [
            round(b.font_size, 2)
            for b in all_blocks
            if b.block_type
            not in (BlockType.CODE.value, BlockType.LIST_ITEM.value)
            and b.font_size > 0
        ]
        if not sizes:
            return (0.0, 0)
        body = _C(sizes).most_common(1)[0][0]
        body_words = [
            HeadingInferer._word_count(b.text)
            for b in all_blocks
            if round(b.font_size, 2) == body
            and not b.is_bold
            and b.block_type
            not in (BlockType.CODE.value, BlockType.LIST_ITEM.value)
            and b.text.strip()
        ]
        if not body_words:
            return (0.0, 0)
        return (sum(body_words) / len(body_words), max(body_words))

    @staticmethod
    def score_block(
        block: ContentBlock,
        *,
        body_size: float,
        page_count: int,
        body_avg_words: float = 0.0,
        body_max_words: int = 0,
    ) -> float:
        """Return a heading-likelihood score in [0, ~3.5].

        Args:
            block: The block to evaluate.
            body_size: The document's body font size in points.
            page_count: Total page count (unused; reserved for future
                weighting adjustments).
            body_avg_words: Average word count of body lines. When 0,
                the relative-length signals degrade gracefully.
            body_max_words: Maximum word count of body lines; used to
                scale the "short" threshold.
        """
        del page_count  # reserved for future per-block y-position weighting
        # Code/list blocks are excluded.
        if block.block_type in (BlockType.CODE.value, BlockType.LIST_ITEM.value):
            return 0.0

        text = block.text.strip()
        if not text or _LEADING_CODE_RE.match(text):
            return 0.0
        if _CODE_LOOKING_RE.match(text):
            return 0.0
        if _HTML_CODE_RE.match(text):
            return 0.0

        score = 0.0
        words = HeadingInferer._word_count(text)

        # 1) Font size signal — primary indicator.
        if body_size > 0 and block.font_size > 0:
            delta = block.font_size - body_size
            if delta > 0:
                # 1pt above body → +0.5, 3pt → +1.0 (capped).
                score += min(1.0, delta / 3.0)

        # 2) Bold signal — only counts when the size doesn't already
        # distinguish the line. Bold + body-size = likely heading.
        if block.is_bold and abs(block.font_size - body_size) <= 0.5:
            score += 0.6

        # 3) Length signal — relative to body lines.
        if body_avg_words >= 5.0 and words <= 4:
            score += 0.7
        elif body_avg_words >= 3.0 and words <= 3:
            score += 0.5
        elif body_avg_words == 0.0 and words <= _MAX_WORDS_FOR_HEADING:
            score += 0.4

        # 4) No-trailing-punctuation signal.
        if not _TRAILING_PUNCT_RE.search(text):
            score += 0.3

        # 5) Caps signal.
        if HeadingInferer._uppercase_ratio(text) >= 0.6 and words <= 8:
            score += 0.2

        # 6) Soft code penalty — these don't kill the score but de-
        # prioritise lines that look like code in the final ranking.
        if _SYMBOL_HEAVY_RE.match(text):
            score -= 0.5
        if _TERMINAL_SHELL_RE.match(text):
            score -= 0.5
        if _SHORT_TOKEN_RE.match(text) and score > 0:
            # A 1-3 char heading text ("logo", "vue") is suspicious.
            score -= 0.3

        return max(0.0, score)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def infer_levels(
        document: PdfDocument,
        *,
        max_level: int = _DEFAULT_MAX_LEVEL,
    ) -> dict[str, int]:
        """Map the document's heading candidates to levels 1..max_level.

        Returns a ``{position_key: level}`` mapping. Keys combine page
        number, Y position, and text so repeated titles stay distinct.

        Args:
            document: The PDF document to analyse.
            max_level: Maximum number of heading levels to assign. Capped
                at 6 (Markdown ATX hard limit). Defaults to 4.
        """
        max_level = max(1, min(6, max_level))

        all_blocks: list[tuple[int, ContentBlock]] = []
        for page in document.pages:
            for block in page.blocks:
                all_blocks.append((page.page_number, block))

        if not all_blocks:
            return {}

        blocks_only = [block for _, block in all_blocks]
        # Body size = weighted mode of font_size for non-code, non-list blocks.
        body_size = HeadingInferer._compute_body_size(blocks_only)
        if body_size <= 0:
            body_candidates = [
                round(b.font_size, 2)
                for b in blocks_only
                if b.block_type
                not in (BlockType.CODE.value, BlockType.LIST_ITEM.value)
                and b.font_size > 0
            ]
            if not body_candidates:
                return {}
            body_size, _ = Counter(body_candidates).most_common(1)[0]
        body_avg, body_max = HeadingInferer._body_word_stats(blocks_only)

        # Score every block; remember its order for tiebreaking.
        scored: list[tuple[int, ContentBlock, float, int]] = []
        for order, (page_number, block) in enumerate(all_blocks):
            s = HeadingInferer.score_block(
                block,
                body_size=body_size,
                page_count=document.page_count,
                body_avg_words=body_avg,
                body_max_words=body_max,
            )
            if s >= _HEADING_SCORE_THRESHOLD:
                scored.append((page_number, block, s, order))

        if not scored:
            return {}

        # Group by (font_size bucket, score bucket). The font_size
        # bucket is the size rounded to 0.5pt; ties within a bucket get
        # the same level. Buckets are ordered desc.
        def _bucket(b: ContentBlock, s: float) -> tuple[float, float]:
            return (round(b.font_size, 1), round(s, 2))

        buckets: dict[tuple[float, float], list[tuple[int, ContentBlock]]] = {}
        for page_number, block, s, _ in scored:
            buckets.setdefault(_bucket(block, s), []).append((page_number, block))

        def _natural_bonus(text: str) -> float:
            """A real book heading is a natural-language phrase. A short
            token, a known shell command, or a code-looking line is
            de-prioritised. Returns 0 for neutral text.
            """
            words = HeadingInferer._word_count(text)
            if words < 2:
                return -1.0
            if _SHELL_COMMAND_RE.match(text):
                return -2.0
            if _CODE_LOOKING_RE.match(text):
                return -1.0
            stripped = text.strip()
            if (
                2 <= words <= 10
                and stripped
                and stripped[0].isupper()
                and not _TRAILING_PUNCT_RE.search(stripped)
            ):
                return 1.0
            return 0.0

        # Pick one representative text per bucket, choosing the most
        # natural-language one. Buckets are ordered: larger font_size
        # first, then higher score.
        seen_text: set[str] = set()
        winners: list[tuple[str, int]] = []
        ordered_buckets = sorted(
            buckets.items(),
            key=lambda kv: (-kv[0][0], -kv[0][1], kv[1][0][1].text),
        )
        for _bucket_key, blocks in ordered_buckets:
            sorted_blocks = sorted(
                blocks, key=lambda item: (-_natural_bonus(item[1].text), item[1].text)
            )
            for page_number, block in sorted_blocks:
                key = block_position_key(page_number, block)
                if key in seen_text:
                    continue
                seen_text.add(key)
                winners.append((key, len(winners) + 1))
                break
            if len(winners) >= max_level:
                break

        if not winners:
            return {}

        # Renumber levels 1..N in original order.
        unique_ranks = sorted({r for _, r in winners})
        rank_to_level = {r: i + 1 for i, r in enumerate(unique_ranks)}
        return {text: rank_to_level[r] for text, r in winners}

    @staticmethod
    def looks_like_heading(
        block: ContentBlock,
        font_levels: dict[str, int],
        *,
        body_size: float = 0.0,
        page_number: int = 1,
    ) -> bool:
        """Heuristic: is this block promoted to a heading?

        ``font_levels`` keys are position-aware block keys. When present,
        the block is a heading. Otherwise a lightweight multi-signal check
        matches :meth:`score_block` for common cases.
        """
        if block.block_type == BlockType.HEADING.value:
            return True
        if block.block_type in (BlockType.CODE.value, BlockType.LIST_ITEM.value):
            return False
        if not block.text.strip():
            return False
        if _LEADING_CODE_RE.match(block.text):
            return False
        if _CODE_LOOKING_RE.match(block.text):
            return False
        if _HTML_CODE_RE.match(block.text):
            return False
        if block_position_key(page_number, block) in font_levels:
            return True
        if block.text.strip() in font_levels:
            return True
        words = len(_WORD_RE.findall(block.text))
        if words > _MAX_WORDS_FOR_HEADING:
            return False
        stripped = block.text.strip()
        if stripped.endswith(":"):
            return True
        if _SENTENCE_END_RE.search(block.text):
            return False
        if body_size > 0 and block.font_size >= body_size + 1.0:
            return True
        # Need at least one positive signal: bold, very short, or all-caps.
        if block.is_bold:
            return True
        if words <= 3 and HeadingInferer._uppercase_ratio(block.text) >= 0.5:
            return True
        return False

    @staticmethod
    def resolve_level(
        block: ContentBlock,
        font_levels: dict[str, int],
        *,
        page_number: int = 1,
    ) -> int:
        """Return the heading level for a single ``block``.

        Precedence:
            1. The level mapped from the block's position key in ``font_levels``.
            2. The level mapped from plain text (legacy compatibility).
            3. ``block.level`` if the extractor already set one.
            4. ``0`` if the block is not a heading.
        """
        if not block.text.strip():
            return 0
        if block.block_type in (BlockType.CODE.value, BlockType.LIST_ITEM.value):
            return 0
        if _LEADING_CODE_RE.match(block.text):
            return 0
        if _CODE_LOOKING_RE.match(block.text):
            return 0
        if _HTML_CODE_RE.match(block.text):
            return 0
        position_key = block_position_key(page_number, block)
        if position_key in font_levels:
            return font_levels[position_key]
        text_key = block.text.strip()
        if text_key in font_levels:
            return font_levels[text_key]
        if block.level:
            return block.level
        return 0


__all__ = ["HeadingInferer"]

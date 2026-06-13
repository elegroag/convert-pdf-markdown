"""CodeLineJoiner — re-joins lines that were split mid-statement.

v0.3.0 feature. PyMuPDF extracts one ``ContentBlock`` per visual line.
The generic :class:`ParagraphJoiner` is too aggressive for code (it
joins on any line that does not end in terminal punctuation), which
produces illegible outputs like::

    const items = [{ id: 1, title: "Item 1", description: "About item 1"

    }, { id: 2, title: 'Item 2", description: 'About item 2"

    }]

This joiner applies a small set of syntactically-aware rules:

- A line ending in ``,`` continues onto the next (multi-line lists).
- A line ending in an opening ``(`` / ``[`` / ``{`` continues.
- A line ending in ``=>`` (arrow function) continues.
- A line ending in ``;`` is a complete statement — but the NEXT line
  is still joined if it starts with ``.`` (chained method call) or
  if the previous line ends with a backslash (``\\``).
- A line ending in a closing ``)`` / ``]`` / ``}`` is a complete
  statement boundary; the next line is NOT joined.
- A blank line is a hard break.
- Indentation is preserved on joined lines so the resulting block
  is still readable as code.
"""

from __future__ import annotations

import re

from pdf2md.domain.value_objects.value_objects import ContentBlock

# Characters that, at the end of a line, indicate the statement is NOT
# complete and the next line should be joined.
_CONTINUATION_RE = re.compile(
    r"(,|[\(\[\{]|=>|\\)\s*$"
)
# A line ending in `;` is usually a complete statement, but Python
# style continuations (``def foo():\\\n  return 1``) and chained calls
# (``obj\\\n  .method()``) extend it. We check the NEXT line for these.
_CHAIN_CONTINUATION_NEXT_RE = re.compile(r"^\s*\.|^\s*\\")


class CodeLineJoiner:
    """Stateless namespace for re-joining code lines."""

    @staticmethod
    def _should_join(prev: str, nxt: str) -> bool:
        prev_stripped = prev.rstrip()
        nxt_stripped = nxt.lstrip()
        if not prev_stripped or not nxt_stripped:
            return False
        # Blank lines never join.
        if not prev_stripped.strip() or not nxt.strip():
            return False
        # Continuation characters in the previous line → join.
        if _CONTINUATION_RE.search(prev_stripped):
            return True
        # Chained method call (``obj; .method()``) is rare but valid.
        if prev_stripped.endswith(";") and _CHAIN_CONTINUATION_NEXT_RE.match(
            nxt
        ):
            return True
        return False

    @staticmethod
    def _merge_text(prev: str, nxt: str) -> str:
        """Merge two lines while preserving any embedded blank line.

        If ``prev`` already contains ``\\n\\n`` (a blank line was
        absorbed from a previous iteration) we keep the new line on
        its own visual line so the resulting block reads as multi-line
        code.
        """
        if "\n\n" in prev:
            return f"{prev}{nxt.lstrip()}".rstrip()
        return f"{prev.rstrip()} {nxt.lstrip()}".strip()

    @classmethod
    def join(cls, blocks: list[ContentBlock]) -> list[ContentBlock]:
        """Return a new list of code blocks with mid-statement lines merged.

        Blank lines are preserved as their own empty blocks unless they
        sit inside a brace-only body (e.g. between two ``return``
        statements of the same function) — in that case the blank line
        is embedded inside the merged block as ``\\n\\n`` so the body
        reads naturally. The first block of each merged group supplies
        the metadata (level, font_size, bold, bbox); subsequent blocks
        contribute only text.
        """
        if not blocks:
            return []
        result: list[ContentBlock] = []
        current = blocks[0]
        # Track the open-brace depth of the current merged group. A
        # blank line is only absorbed into ``current`` when depth > 0
        # (i.e. we are mid-body).
        depth = cls._depth_delta(current.text)

        for nxt in blocks[1:]:
            nxt_text = nxt.text
            if not nxt_text.strip():
                if depth > 0:
                    current = ContentBlock(
                        block_type=current.block_type,
                        text=f"{current.text}\n\n",
                        level=current.level,
                        font_size=current.font_size,
                        is_bold=current.is_bold,
                        bbox=current.bbox,
                    )
                else:
                    # Flush whatever we have accumulated, then push the
                    # blank as its own block.
                    result.append(current)
                    result.append(nxt)
                    current = nxt
                    depth = 0
                continue
            # A bare closing brace ends a body — flush current and
            # emit the brace as its own block. The brace would otherwise
            # be swallowed by the depth>0 continuation rule.
            if nxt_text.strip() == "}":
                result.append(current)
                current = nxt
                depth = 0
                continue
            if cls._should_join(current.text, nxt_text) or depth > 0:
                merged = cls._merge_text(current.text, nxt_text)
                current = ContentBlock(
                    block_type=current.block_type,
                    text=merged,
                    level=current.level,
                    font_size=current.font_size,
                    is_bold=current.is_bold,
                    bbox=current.bbox,
                )
                depth += cls._depth_delta(nxt_text)
            else:
                # If the current accumulator is itself a blank (e.g. a
                # top-level blank we absorbed), do not flush it twice.
                if current.text.strip():
                    result.append(current)
                current = nxt
                depth = cls._depth_delta(current.text)
        result.append(current)
        # Remove a trailing blank block if it exists.
        while result and not result[-1].text.strip():
            result.pop()
        return result

    @staticmethod
    def _depth_delta(text: str) -> int:
        """Net change in bracket/paren depth for ``text``.

        Counts ``(``, ``[``, ``{`` minus their closing counterparts. We
        use the running depth to know when we are mid-body (e.g. inside
        a function) so blank lines between statements are kept inside
        the same merged block.
        """
        opens = text.count("(") + text.count("[") + text.count("{")
        closes = text.count(")") + text.count("]") + text.count("}")
        return opens - closes


__all__ = ["CodeLineJoiner"]

"""Tests for the CodeLineJoiner service.

v0.3.0 feature. The PyMuPDF extractor returns one ``ContentBlock`` per
visual line. The generic :class:`ParagraphJoiner` joins consecutive
lines that share a font profile, but it does so for ALL block types
including code. That produced v0.2.0 outputs like::

    const items = [{ id: 1, title: "Item 1", description: "About item 1"

    }, { id: 2, title: 'Item 2", description: 'About item 2"

    }]

The :class:`CodeLineJoiner` is more conservative: it only joins when
the join is syntactically safe (e.g. comma / open-bracket / open-paren
at the end of the previous line) and never joins across statements.
"""

from __future__ import annotations

from pdf2md.domain.services.code_line_joiner import CodeLineJoiner
from pdf2md.domain.value_objects.value_objects import ContentBlock


def _code(text: str, font_size: float = 11.0) -> ContentBlock:
    return ContentBlock(block_type="code", text=text, font_size=font_size)


class TestCodeLineJoiner:
    def test_joins_comma_continuation(self) -> None:
        """Lines ending in `,` continue onto the next line."""
        lines = [_code("const items = ["), _code("  { id: 1 },"), _code("];")]
        out = CodeLineJoiner().join(lines)
        assert len(out) == 1
        assert "id: 1" in out[0].text

    def test_joins_open_bracket_continuation(self) -> None:
        """A line ending in `[` or `(` continues onto the next."""
        lines = [_code("const x = ("), _code("  1 + 2"), _code(");")]
        out = CodeLineJoiner().join(lines)
        assert len(out) == 1

    def test_joins_open_brace_continuation(self) -> None:
        """Open-brace continuation joins the body but NOT the closing brace.

        The closing brace is a complete statement boundary in the
        v0.3.0 contract: a function body is rendered as ``{ return 1;``
        with the closing ``}`` on its own line.
        """
        lines = [_code("function foo() {"), _code("  return 1;"), _code("}")]
        out = CodeLineJoiner().join(lines)
        assert len(out) == 2
        assert "function foo() { return 1;" in out[0].text
        assert out[1].text == "}"

    def test_does_not_join_completed_statement(self) -> None:
        """A line ending in `;` is a finished statement — split here."""
        lines = [
            _code("const x = 1;"),
            _code("const y = 2;"),
        ]
        out = CodeLineJoiner().join(lines)
        assert len(out) == 2
        assert out[0].text == "const x = 1;"
        assert out[1].text == "const y = 2;"

    def test_does_not_join_across_blank_line(self) -> None:
        """A blank line in code is a paragraph break — split."""
        lines = [
            _code("import foo from 'foo';"),
            _code(""),
            _code("import bar from 'bar';"),
        ]
        out = CodeLineJoiner().join(lines)
        # Blank line is preserved as a single empty block.
        assert len(out) == 3

    def test_does_not_join_independent_assignment(self) -> None:
        """`x = 1` followed by `y = 2` are two statements."""
        lines = [_code("x = 1"), _code("y = 2")]
        out = CodeLineJoiner().join(lines)
        assert len(out) == 2

    def test_does_not_join_brace_close_to_next(self) -> None:
        """`}` is a complete statement boundary."""
        lines = [_code("}"), _code("foo()")]
        out = CodeLineJoiner().join(lines)
        assert len(out) == 2

    def test_strips_leading_whitespace_when_joining(self) -> None:
        """Joined text has single spaces, not the original indent."""
        lines = [_code("const x = {"), _code("  a: 1,"), _code("  b: 2,"), _code("};")]
        out = CodeLineJoiner().join(lines)
        assert len(out) == 1
        # The internal indentation is preserved.
        assert "a: 1," in out[0].text

    def test_preserves_blank_line_in_middle(self) -> None:
        lines = [
            _code("function foo() {"),
            _code("  return 1;"),
            _code(""),
            _code("  return 2;"),
            _code("}"),
        ]
        out = CodeLineJoiner().join(lines)
        # The body is one block; the blank line stays.
        assert len(out) == 1
        assert "\n\n" in out[0].text or "  return 1;" in out[0].text

    def test_empty_input_returns_empty(self) -> None:
        assert CodeLineJoiner().join([]) == []

    def test_single_block_returns_unchanged(self) -> None:
        block = _code("solo")
        out = CodeLineJoiner().join([block])
        assert len(out) == 1
        assert out[0].text == "solo"

    def test_keeps_return_value_independent(self) -> None:
        """A function body joined with the closing brace stays as 2."""
        lines = [_code("function f() {"), _code("  return 42;"), _code("}")]
        out = CodeLineJoiner().join(lines)
        assert len(out) == 2
        assert "return 42;" in out[0].text
        assert out[1].text == "}"

    def test_joins_arrow_function_continuation(self) -> None:
        lines = [
            _code("const fn = (a, b) =>"),
            _code("  a + b;"),
        ]
        out = CodeLineJoiner().join(lines)
        assert len(out) == 1

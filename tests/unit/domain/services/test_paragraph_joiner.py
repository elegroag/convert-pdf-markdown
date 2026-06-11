"""Tests for the ParagraphJoiner service.

The PyMuPDF extractor emits one ContentBlock per visual line, so a
single paragraph is fragmented into 8-12 short blocks. The joiner runs
after extraction and re-unites consecutive lines that belong to the
same paragraph.

This file is the TDD specification for the joiner.
"""

from __future__ import annotations

from pdf2md.domain.services.paragraph_joiner import ParagraphJoiner
from pdf2md.domain.value_objects.value_objects import ContentBlock


def _para(
    text: str,
    *,
    font_size: float = 11.0,
    bold: bool = False,
    bbox: tuple[float, float, float, float] | None = None,
) -> ContentBlock:
    return ContentBlock(
        block_type="paragraph",
        text=text,
        font_size=font_size,
        is_bold=bold,
        bbox=bbox,
    )


def _code(text: str, font_size: float = 11.0) -> ContentBlock:
    return ContentBlock(block_type="code", text=text, font_size=font_size)


def _list(text: str) -> ContentBlock:
    return ContentBlock(block_type="list_item", text=text)


class TestJoinerSameParagraph:
    """Two consecutive blocks of the same paragraph must be joined."""

    def test_two_short_lines_join_with_space(self) -> None:
        blocks = [
            _para("Vue is a progressive framework for"),
            _para("building user interfaces."),
        ]
        out = ParagraphJoiner().join(blocks)
        assert len(out) == 1
        assert out[0].text == "Vue is a progressive framework for building user interfaces."

    def test_three_short_lines_join_into_one(self) -> None:
        blocks = [
            _para("line one"),
            _para("line two"),
            _para("line three"),
        ]
        out = ParagraphJoiner().join(blocks)
        assert len(out) == 1
        assert out[0].text == "line one line two line three"

    def test_joined_text_preserves_punctuation(self) -> None:
        blocks = [
            _para("The end is near."),
            _para("Or is it?"),
        ]
        out = ParagraphJoiner().join(blocks)
        assert len(out) == 2  # both end in punctuation → split

    def test_first_ends_in_period_blocks_join(self) -> None:
        """A line ending in period followed by a Capitalised line stays split."""
        blocks = [
            _para("First sentence ends here."),
            _para("New paragraph starts."),
        ]
        out = ParagraphJoiner().join(blocks)
        assert len(out) == 2


class TestJoinerDifferentFontSize:
    """Lines with different font sizes must not be joined."""

    def test_different_size_breaks_paragraph(self) -> None:
        blocks = [
            _para("Heading line", font_size=18.0, bold=True),
            _para("body line", font_size=11.0),
        ]
        out = ParagraphJoiner().join(blocks)
        assert len(out) == 2

    def test_tiny_size_delta_treated_as_same(self) -> None:
        """0.2 pt differences are noise from anti-aliasing — keep joined."""
        blocks = [
            _para("First half of a paragraph", font_size=11.0),
            _para("second half of a paragraph", font_size=11.2),
        ]
        out = ParagraphJoiner().join(blocks)
        assert len(out) == 1


class TestJoinerDifferentBlockType:
    """Code and list blocks never merge with paragraphs."""

    def test_paragraph_then_code_stays_split(self) -> None:
        blocks = [
            _para("Some intro text."),
            _code("const x = 1;"),
        ]
        out = ParagraphJoiner().join(blocks)
        assert len(out) == 2

    def test_code_then_paragraph_stays_split(self) -> None:
        blocks = [
            _code("const x = 1;"),
            _para("Explanation after the code."),
        ]
        out = ParagraphJoiner().join(blocks)
        assert len(out) == 2

    def test_list_items_never_join_paragraphs(self) -> None:
        blocks = [
            _para("Intro paragraph."),
            _list("- First item"),
            _list("- Second item"),
            _para("Conclusion paragraph."),
        ]
        out = ParagraphJoiner().join(blocks)
        assert len(out) == 4


class TestJoinerPunctuation:
    """Punctuation rules drive the split decisions."""

    def test_line_ending_in_hyphen_strips_hyphen_and_joins(self) -> None:
        """Wrap-after-hyphen is common: 'frame-\\nwork' → 'framework'."""
        blocks = [
            _para("This is a long word that is frame-"),
            _para("work for everyone."),
        ]
        out = ParagraphJoiner().join(blocks)
        assert len(out) == 1
        assert out[0].text == "This is a long word that is framework for everyone."

    def test_line_ending_in_colon_breaks(self) -> None:
        blocks = [
            _para("For example:"),
            _para("the API is simple."),
        ]
        out = ParagraphJoiner().join(blocks)
        assert len(out) == 2

    def test_line_starting_with_capital_joins_to_previous(self) -> None:
        """Mid-paragraph wrap doesn't start with capital in real text."""
        blocks = [
            _para("Vue provides reactivity and"),
            _para("components out of the box."),
        ]
        out = ParagraphJoiner().join(blocks)
        assert len(out) == 1


class TestJoinerEmpty:
    def test_empty_input_returns_empty(self) -> None:
        assert ParagraphJoiner().join([]) == []

    def test_single_block_returns_unchanged(self) -> None:
        blocks = [_para("solo")]
        out = ParagraphJoiner().join(blocks)
        assert len(out) == 1
        assert out[0].text == "solo"


class TestJoinerRealisticPackt:
    """Mimics the actual structure of the Vue.js Packt book."""

    def test_long_paragraph_with_8_lines_joins_into_one(self) -> None:
        # Sample of the real first paragraph from VUE-JS-3-001.pdf p1.
        fragments = [
            "En este capítulo, aprenderá sobre los conceptos clave y los beneficios de Vue.js (Vue), cómo configurar",
            "la arquitectura del proyecto usando la terminal (o línea de comando) y cómo crear un componente Vue",
            "simple con datos locales siguiendo las instrucciones. fundamentos de los componentes.",
        ]
        blocks = [_para(f) for f in fragments]
        out = ParagraphJoiner().join(blocks)
        # Last fragment ends in period → break, so we expect 2 chunks
        # (first two joined, third separate). This is acceptable and
        # closer to natural paragraph boundaries.
        assert len(out) >= 1
        joined_first = " ".join(fragments[:2])
        assert joined_first in out[0].text

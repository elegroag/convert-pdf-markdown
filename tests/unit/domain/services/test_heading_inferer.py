"""Tests for the multi-signal HeadingInferer (v0.2.0).

The inferer no longer relies on font size alone. It computes a score for
every block based on multiple signals (font size, font weight, line length,
trailing punctuation, position) and assigns the top-N candidates to
heading levels 1..N. The cap is configurable; default is 4.

These tests pin the new contract so refactors stay within bounds.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf2md.domain.entities.entities import PdfDocument, PdfPage
from pdf2md.domain.services.heading_inferer import HeadingInferer
from pdf2md.domain.value_objects.value_objects import ContentBlock


def _page(*blocks: ContentBlock, page_number: int = 1) -> PdfPage:
    return PdfPage(page_number=page_number, blocks=list(blocks))


def _para(
    text: str,
    size: float = 11.0,
    *,
    bold: bool = False,
    bbox: tuple[float, float, float, float] | None = None,
) -> ContentBlock:
    return ContentBlock(
        block_type="paragraph",
        text=text,
        font_size=size,
        is_bold=bold,
        bbox=bbox,
    )


def _code(text: str, size: float = 11.0) -> ContentBlock:
    return ContentBlock(block_type="code", text=text, font_size=size)


def _list_item(text: str, size: float = 11.0) -> ContentBlock:
    return ContentBlock(block_type="list_item", text=text, font_size=size)


class TestScoring:
    """HeadingInferer.score_block returns a numeric score per signal set."""

    def test_short_bold_line_at_top_scores_higher_than_body(self) -> None:
        """A 3-word bold line with no trailing punctuation scores high."""
        block = _para("Angular versus Vue", bold=True)
        score = HeadingInferer.score_block(block, body_size=11.0, page_count=10)
        assert score >= HeadingInferer.HEADING_SCORE_THRESHOLD

    def test_long_regular_line_with_period_scores_below_threshold(self) -> None:
        """A 30-word regular line ending in period is body text, not a heading."""
        text = (
            "Vue aprovecha la solidez central de Angular y proporciona una mejor "
            "experiencia de desarrollo al eliminar la restricción."
        )
        block = _para(text, bold=False)
        score = HeadingInferer.score_block(block, body_size=11.0, page_count=10)
        assert score < HeadingInferer.HEADING_SCORE_THRESHOLD

    def test_code_block_never_scores_as_heading(self) -> None:
        """A monospaced code block has block_type=code and must be excluded."""
        block = _code("const x = 1;")
        score = HeadingInferer.score_block(block, body_size=11.0, page_count=10)
        assert score == 0.0

    def test_list_item_never_scores_as_heading(self) -> None:
        """List items belong to lists, not the heading hierarchy."""
        block = _list_item("- First item")
        score = HeadingInferer.score_block(block, body_size=11.0, page_count=10)
        assert score == 0.0

    def test_short_all_caps_line_scores_as_heading(self) -> None:
        """Uppercase titles like 'VUE JS 3' get a length+uppercase boost."""
        block = _para("VUE JS 3", bold=True, size=13.0)
        score = HeadingInferer.score_block(block, body_size=11.0, page_count=10)
        assert score >= HeadingInferer.HEADING_SCORE_THRESHOLD

    def test_line_starting_with_hash_is_not_a_heading(self) -> None:
        """Code lines starting with '#' (e.g. python comments) must be ignored."""
        block = _para("# this is a python comment", size=11.0)
        score = HeadingInferer.score_block(block, body_size=11.0, page_count=10)
        assert score == 0.0

    def test_lone_closing_brace_is_not_a_heading(self) -> None:
        """A line that is just `}` is code, not a heading."""
        block = _para("}", size=11.0)
        score = HeadingInferer.score_block(block, body_size=11.0, page_count=10)
        assert score == 0.0

    def test_export_default_is_not_a_heading(self) -> None:
        block = _para("export default {", size=11.0)
        score = HeadingInferer.score_block(block, body_size=11.0, page_count=10)
        assert score == 0.0

    def test_const_declaration_is_not_a_heading(self) -> None:
        block = _para("const x = 1;", size=11.0)
        score = HeadingInferer.score_block(block, body_size=11.0, page_count=10)
        assert score == 0.0


class TestInferLevelsMultiSignal:
    """infer_levels returns a score-ordered mapping of blocks to levels."""

    def test_promotes_short_bold_lines_when_font_size_uniform(self) -> None:
        """PDFs like Packt use uniform 11pt; bold + short must still promote.

        v0.2.0: candidates with the same (font_size, score) bucket
        share one level. Three identical buckets ⇒ one winner.
        """
        doc = PdfDocument(
            file_path=Path("x.pdf"),
            page_count=1,
            pages=[
                _page(
                    _para("body text body text body text body text body text."),
                    _para("Angular versus Vue", bold=True),
                    _para("Reaccionar versus Vue", bold=True),
                    _para("Ventajas de usar Vue para tu proyecto", bold=True),
                ),
            ],
        )
        levels = HeadingInferer().infer_levels(doc)
        # All bold short lines live in one bucket; the most natural
        # text wins the H1 slot.
        assert 1 in levels.values()
        assert any(key.endswith("Angular versus Vue") for key in levels)

    def test_returns_empty_when_document_has_only_body(self) -> None:
        """No short/bold/caps lines → no headings."""
        doc = PdfDocument(
            file_path=Path("x.pdf"),
            page_count=1,
            pages=[
                _page(
                    _para(
                        "This is a long body paragraph with many words "
                        "spanning several lines of text in the document."
                    ),
                    _para(
                        "Another body paragraph that should not be promoted "
                        "to a heading because it is way too long."
                    ),
                ),
            ],
        )
        assert HeadingInferer().infer_levels(doc) == {}

    def test_caps_at_max_level(self) -> None:
        """The number of promoted headings is bounded by max_level."""
        doc = PdfDocument(
            file_path=Path("x.pdf"),
            page_count=1,
            pages=[
                _page(*[_para(f"Heading {i}", bold=True) for i in range(10)]),
            ],
        )
        levels = HeadingInferer().infer_levels(doc, max_level=3)
        assert len(levels) <= 3
        # All assigned levels are 1..max_level.
        for assigned in levels.values():
            assert 1 <= assigned <= 3

    def test_max_level_is_configurable(self) -> None:
        """Pass max_level=4 → up to 4 levels (default v0.2.0 is 4)."""
        doc = PdfDocument(
            file_path=Path("x.pdf"),
            page_count=1,
            pages=[
                _page(
                    *[
                        _para(f"Heading {i}", bold=True, size=12.0 + i * 0.5)
                        for i in range(5)
                    ],
                    _para("body body body body body body body body body body."),
                ),
            ],
        )
        levels_4 = HeadingInferer().infer_levels(doc, max_level=4)
        levels_2 = HeadingInferer().infer_levels(doc, max_level=2)
        assert len(levels_4) >= len(levels_2)

    def test_default_max_level_is_six(self) -> None:
        """The class default must be 6 (Markdown ATX hard limit)."""
        assert HeadingInferer.DEFAULT_MAX_LEVEL == 6


class TestLooksLikeHeading:
    """The new heuristic combines font_levels dict + multi-signal score."""

    def test_short_bold_paragraph_promoted_even_when_size_matches_body(self) -> None:
        """The key fix: 11pt bold short lines must be promoted."""
        block = _para("Angular versus Vue", bold=True)
        assert HeadingInferer().looks_like_heading(block, {}) is True

    def test_long_body_paragraph_not_promoted(self) -> None:
        block = _para(
            "This is a long body paragraph with many words spanning the page.",
        )
        assert HeadingInferer().looks_like_heading(block, {}) is False

    def test_code_block_never_promoted(self) -> None:
        block = _code("const x = 1;")
        assert HeadingInferer().looks_like_heading(block, {}) is False

    def test_block_starting_with_hash_not_promoted(self) -> None:
        block = _para("# python comment line that is reasonably long for testing")
        assert HeadingInferer().looks_like_heading(block, {}) is False

    def test_explicit_heading_type_always_promoted(self) -> None:
        block = ContentBlock(block_type="heading", text="x", font_size=0.0)
        assert HeadingInferer().looks_like_heading(block, {}) is True


class TestResolveLevel:
    """resolve_level returns the assigned level for a promoted block."""

    def test_uses_inferred_levels_map_for_promoted_block(self) -> None:
        block = _para("Angular versus Vue", bold=True)
        levels = {"Angular versus Vue": 1, "Reaccionar versus Vue": 2}
        assert HeadingInferer().resolve_level(block, levels) == 1

    def test_pre_set_level_still_wins(self) -> None:
        block = ContentBlock(
            block_type="heading", text="x", font_size=0.0, level=3
        )
        assert HeadingInferer().resolve_level(block, {}) == 3

    def test_non_promoted_block_returns_zero(self) -> None:
        """A long body paragraph must NOT default to level 1 anymore."""
        block = _para(
            "A long body paragraph that is clearly not a heading by any "
            "heuristic should not be promoted to level 1."
        )
        assert HeadingInferer().resolve_level(block, {}) == 0


class TestBackwardCompatibility:
    """The old tests from v0.1.0 must still pass with the new inferer.

    The font-size-only path must keep working as a degenerate case.
    """

    def test_single_size_above_body_is_h1(self) -> None:
        doc = PdfDocument(
            file_path=Path("x.pdf"),
            page_count=1,
            pages=[
                _page(
                    ContentBlock(block_type="paragraph", text="a", font_size=12.0),
                    ContentBlock(block_type="paragraph", text="b", font_size=12.0),
                    ContentBlock(
                        block_type="paragraph",
                        text="title here",
                        font_size=18.0,
                        is_bold=True,
                    ),
                ),
            ],
        )
        result = HeadingInferer().infer_levels(doc)
        # Title is both larger and bold, must be promoted.
        assert 1 in result.values()

    def test_three_levels_assigned_h1_h2_h3(self) -> None:
        doc = PdfDocument(
            file_path=Path("x.pdf"),
            page_count=1,
            pages=[
                _page(
                    ContentBlock(
                        block_type="paragraph", text="body1", font_size=10.0
                    ),
                    ContentBlock(
                        block_type="paragraph", text="body2", font_size=10.0
                    ),
                    ContentBlock(
                        block_type="paragraph",
                        text="h1 here",
                        font_size=20.0,
                        is_bold=True,
                    ),
                    ContentBlock(
                        block_type="paragraph",
                        text="h2 here",
                        font_size=15.0,
                        is_bold=True,
                    ),
                    ContentBlock(
                        block_type="paragraph",
                        text="h3 here",
                        font_size=12.5,
                        is_bold=True,
                    ),
                ),
            ],
        )
        result = HeadingInferer().infer_levels(doc)
        assert sorted(result.values()) == [1, 2, 3]

    def test_body_size_is_the_most_frequent(self) -> None:
        doc = PdfDocument(
            file_path=Path("x.pdf"),
            page_count=1,
            pages=[
                _page(
                    ContentBlock(block_type="paragraph", text="a", font_size=10.0),
                    ContentBlock(block_type="paragraph", text="b", font_size=10.0),
                    ContentBlock(block_type="paragraph", text="c", font_size=10.0),
                    ContentBlock(block_type="paragraph", text="d", font_size=10.0),
                    ContentBlock(
                        block_type="paragraph",
                        text="title here",
                        font_size=20.0,
                        is_bold=True,
                    ),
                ),
            ],
        )
        result = HeadingInferer().infer_levels(doc)
        assert 10.0 not in result

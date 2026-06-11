"""Tests for the span-joining logic in the PyMuPDF extractor.

v0.2.0: when a PDF line contains multiple spans, the extractor joins
them with a single space when the previous span does NOT end in
whitespace and the next span does NOT start with punctuation. This
fixes cases like ``"Hola"él`` → ``"Hola" él``.
"""

from __future__ import annotations

from pdf2md.infrastructure.extractors.pymupdf_extractor import _join_spans


def _span(text: str):
    return {"text": text, "size": 11.0, "font": "Arial", "flags": 0}


class TestJoinSpans:
    def test_empty_returns_empty(self) -> None:
        assert _join_spans([]) == ""

    def test_single_span(self) -> None:
        assert _join_spans([_span("hello")]) == "hello"

    def test_two_spans_joined_with_space(self) -> None:
        """Two word-like spans get a single space between them."""
        out = _join_spans([_span("Hello"), _span("world")])
        assert out == "Hello world"

    def test_span_ending_in_space_not_doubled(self) -> None:
        """A trailing space in the previous span is respected (no extra)."""
        out = _join_spans([_span("Hello "), _span("world")])
        assert out == "Hello world"

    def test_next_span_starting_with_punctuation_no_space(self) -> None:
        """``Foo`` + ``,bar`` → ``Foo,bar`` (no space before comma)."""
        out = _join_spans([_span("Foo"), _span(",bar")])
        assert out == "Foo,bar"

    def test_span_with_closing_quote_then_word(self) -> None:
        out = _join_spans([_span("\"Hola\""), _span("él")])
        assert out == "\"Hola\" él"

    def test_span_starting_with_already_space_no_double(self) -> None:
        out = _join_spans([_span("Hello"), _span(" world")])
        assert out == "Hello world"

    def test_preserve_internal_whitespace(self) -> None:
        """The function only inserts ONE space when needed."""
        out = _join_spans([_span("a"), _span("b"), _span("c")])
        assert out == "a b c"

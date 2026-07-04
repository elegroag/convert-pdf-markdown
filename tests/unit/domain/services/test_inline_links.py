"""Tests for inline link application."""

from __future__ import annotations

from pdf2md.domain.services.inline_links import apply_inline_links
from pdf2md.domain.value_objects.value_objects import ContentBlock, Link


def test_applies_markdown_link_for_matching_text() -> None:
    block = ContentBlock(block_type="paragraph", text="Visit Example site today.")
    links = [
        Link(
            url="https://example.com",
            text="Example site",
            page_number=1,
            bbox=(0.0, 0.0, 10.0, 10.0),
        )
    ]
    out = apply_inline_links(block.text, links, block=block)
    assert out == "Visit [Example site](https://example.com) today."


def test_skips_short_labels_that_match_inside_words() -> None:
    block = ContentBlock(block_type="paragraph", text="Some body text.")
    links = [Link(url="https://x.com", text="x", page_number=1)]
    out = apply_inline_links(block.text, links, block=block)
    assert out == "Some body text."

"""Tests for AnchorSlug.

Slugs are used both for filesystem naming (file_storage) and for
in-document Markdown anchors. The rules are pinned in this test file
to prevent silent drift.
"""

from __future__ import annotations

import pytest

from pdf2md.domain.services.anchor_slug import AnchorSlug


class TestAnchorSlug:
    """AnchorSlug produces GitHub-style slugs from arbitrary strings."""

    def test_lowercases_input(self) -> None:
        assert AnchorSlug.slugify("Hello World") == "hello-world"

    def test_replaces_whitespace_with_hyphen(self) -> None:
        assert AnchorSlug.slugify("foo  bar\tbaz") == "foo-bar-baz"

    def test_drops_punctuation(self) -> None:
        assert AnchorSlug.slugify("Hello, World!") == "hello-world"

    def test_preserves_hyphens_and_underscores(self) -> None:
        assert AnchorSlug.slugify("foo-bar_baz") == "foo-bar_baz"

    def test_collapses_repeated_separators(self) -> None:
        assert AnchorSlug.slugify("foo!!!bar???baz") == "foo-bar-baz"

    def test_strips_leading_and_trailing_separators(self) -> None:
        assert AnchorSlug.slugify("---foo---") == "foo"

    def test_returns_fallback_for_empty_input(self) -> None:
        assert AnchorSlug.slugify("") == "document"
        assert AnchorSlug.slugify("   ") == "document"
        assert AnchorSlug.slugify("!!!") == "document"

    def test_preserves_digits(self) -> None:
        assert AnchorSlug.slugify("Chapter 12") == "chapter-12"

    def test_normalizes_accents_to_ascii(self) -> None:
        assert AnchorSlug.slugify("Capítulo 1: Introducción") == "capitulo-1-introduccion"

    def test_deduplicates_when_requested(self) -> None:
        used = {"hello-world"}
        assert AnchorSlug.unique_slug("Hello World", used) == "hello-world-1"

    def test_dedup_increments_until_free(self) -> None:
        used = {"foo", "foo-1", "foo-2"}
        assert AnchorSlug.unique_slug("Foo", used) == "foo-3"

    def test_dedup_does_not_mutate_caller_set(self) -> None:
        used = {"foo"}
        AnchorSlug.unique_slug("Foo", used)
        assert used == {"foo"}

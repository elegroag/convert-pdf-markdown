"""Tests for FrontmatterBuilder.

The builder renders a YAML frontmatter string from a :class:`PdfMetadata`
+ page count. Fields with empty values are dropped; the closing fence
is always present.
"""

from __future__ import annotations

import pytest

from pdf2md.domain.entities.entities import PdfMetadata
from pdf2md.domain.services.frontmatter_builder import FrontmatterBuilder


class TestFrontmatterBuilder:
    """FrontmatterBuilder.build produces the YAML block per spec §5.1."""

    def test_empty_metadata_with_zero_pages_returns_empty(self) -> None:
        """No metadata and no pages -> empty string (caller should skip)."""
        assert FrontmatterBuilder().build(PdfMetadata(), page_count=0) == ""

    def test_emits_opening_and_closing_fence(self) -> None:
        out = FrontmatterBuilder().build(PdfMetadata(title="X"), page_count=1)
        assert out.startswith("---\n")
        assert out.endswith("\n---")
        assert "title: \"X\"" in out
        assert "pages: 1" in out

    def test_skips_empty_fields(self) -> None:
        out = FrontmatterBuilder().build(
            PdfMetadata(title="T", author="", subject=""),
            page_count=42,
        )
        assert "title: \"T\"" in out
        assert "author" not in out
        assert "subject" not in out
        assert "pages: 42" in out

    def test_escapes_double_quotes(self) -> None:
        out = FrontmatterBuilder().build(PdfMetadata(title='He said "hi"'), page_count=1)
        assert 'title: "He said \\"hi\\""' in out

    def test_escapes_backslashes(self) -> None:
        out = FrontmatterBuilder().build(PdfMetadata(author="a\\b"), page_count=1)
        assert 'author: "a\\\\b"' in out

    def test_emits_all_fields(self) -> None:
        meta = PdfMetadata(
            title="Clean Code",
            author="Robert C. Martin",
            subject="Programming",
            creator="LaTeX",
            producer="pdfTeX",
            creation_date="2008-08-01",
        )
        out = FrontmatterBuilder().build(meta, page_count=431)
        # v0.2.0: each field may be a quoted string on its own line or a
        # block scalar (key on one line, value on the following indented
        # lines). Assert each key appears and each value appears in the
        # document.
        for value in [
            '"Clean Code"',
            '"Robert C. Martin"',
            '"Programming"',
            '"LaTeX"',
            '"pdfTeX"',
            "2008-08-01",
        ]:
            assert value in out, f"{value!r} missing from {out!r}"
        assert "pages: 431" in out

    def test_uses_creation_date_key(self) -> None:
        """``PdfMetadata.creation_date`` maps to ``created:`` in YAML.

        v0.2.0: dates starting with a digit are emitted as a block
        scalar to prevent strict YAML parsers from interpreting them
        as native date objects.
        """
        out = FrontmatterBuilder().build(
            PdfMetadata(creation_date="2024-01-01"), page_count=1
        )
        assert "created: |" in out
        assert "2024-01-01" in out
        assert "creation_date" not in out

    def test_pages_is_integer_not_string(self) -> None:
        """``pages:`` is unquoted (numeric)."""
        out = FrontmatterBuilder().build(PdfMetadata(title="X"), page_count=7)
        assert "pages: 7\n" in out
        assert 'pages: "7"' not in out

    def test_yaml_value_with_colon_uses_block_scalar(self) -> None:
        """PDF creation_date ``D:20260605211504-05'00'`` is normalised to
        ISO 8601 and emitted as a block scalar (the raw format contains
        both a colon and an apostrophe, which break YAML round-trips)."""
        out = FrontmatterBuilder().build(
            PdfMetadata(creation_date="D:20260605211504-05'00'"),
            page_count=1,
        )
        # ISO 8601 form in a block scalar.
        assert "created: |" in out
        assert "2026-06-05T21:15:04-05:00" in out
        # Raw D: prefix must not appear.
        assert "D:2026" not in out

    def test_yaml_value_with_apostrophe_uses_block_scalar(self) -> None:
        out = FrontmatterBuilder().build(
            PdfMetadata(producer="Writer's Block v1.0"),
            page_count=1,
        )
        assert "producer: |" in out

    def test_yaml_value_with_leading_hash_uses_block_scalar(self) -> None:
        """A title starting with # would be interpreted as a YAML comment."""
        out = FrontmatterBuilder().build(
            PdfMetadata(title="# Not a comment"),
            page_count=1,
        )
        assert "title: |" in out

    def test_pdf_date_is_normalised_to_iso8601(self) -> None:
        """The ``D:YYYYMMDDHHMMSS±HH'MM'`` format is converted to ISO 8601
        and emitted as a block scalar (because the ISO form starts with a
        digit, which would otherwise parse as a YAML number/date)."""
        out = FrontmatterBuilder().build(
            PdfMetadata(creation_date="D:20260605211504-05'00'"),
            page_count=1,
        )
        # Must NOT contain the raw D: prefix.
        assert "D:2026" not in out
        # Must contain the normalised ISO 8601 form in a block scalar.
        assert "created: |" in out
        assert "2026-06-05T21:15:04-05:00" in out

    def test_unparseable_date_with_unsafe_chars_falls_back_to_block_scalar(
        self,
    ) -> None:
        """A date that can't be parsed but contains unsafe chars is preserved
        verbatim in a block scalar."""
        out = FrontmatterBuilder().build(
            PdfMetadata(creation_date="yesterday: maybe"),
            page_count=1,
        )
        assert "created: |" in out
        assert "yesterday: maybe" in out

    def test_yaml_output_parses_with_strict_parser(self) -> None:
        """The full output must round-trip through yaml.safe_load without error."""
        import yaml  # type: ignore[import-untyped]

        meta = PdfMetadata(
            title='Title: with colons "and quotes"',
            author="A. B.",
            subject="Subject with a #hash",
            creator="LibreOffice 26.2.3.2 (X86_64)",
            producer="Writer's Block",
            creation_date="D:20260605211504-05'00'",
        )
        out = FrontmatterBuilder().build(meta, page_count=107)
        # Strip the leading and trailing --- fences and parse the body.
        # The body is everything between the first "\n---\n" and the last
        # "\n---".
        body = out.split("\n", 1)[1].rsplit("\n", 1)[0]
        parsed = yaml.safe_load(body)
        assert isinstance(parsed, dict)
        assert parsed["pages"] == 107
        assert "with colons" in parsed["title"]
        assert "with a" in parsed["subject"]

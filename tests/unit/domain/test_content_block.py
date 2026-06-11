"""Tests for ContentBlock, PageContent, and Link value objects."""

from __future__ import annotations

from pdf2md.domain.value_objects.enums import BlockType
from pdf2md.domain.value_objects.value_objects import (
    ContentBlock,
    Link,
    PageContent,
    TableCell,
)


class TestContentBlock:
    """Tests for :class:`ContentBlock`."""

    def test_frozen_blocks_mutation(self) -> None:
        """ContentBlock is frozen."""
        block = ContentBlock(block_type=BlockType.PARAGRAPH.value, text="hi")
        try:
            block.text = "bye"  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError("ContentBlock should be frozen")

    def test_default_level(self) -> None:
        """A non-heading block defaults to level 0."""
        block = ContentBlock(block_type="paragraph", text="hi")
        assert block.level == 0
        assert block.font_size == 0.0
        assert block.is_bold is False

    def test_heading_levels(self) -> None:
        """A heading can carry a level 1-6."""
        block = ContentBlock(
            block_type=BlockType.HEADING.value, text="Title", level=2
        )
        assert block.level == 2


class TestTableCell:
    """Tests for :class:`TableCell`."""

    def test_default_is_header(self) -> None:
        """A cell is not a header by default."""
        cell = TableCell(text="value")
        assert cell.is_header is False


class TestLink:
    """Tests for :class:`Link`."""

    def test_internal_link_flag(self) -> None:
        """``is_internal`` distinguishes in-document links from external ones."""
        external = Link(
            url="https://example.com", text="x", page_number=1, is_internal=False
        )
        internal = Link(
            url="#section", text="x", page_number=2, is_internal=True
        )
        assert external.is_internal is False
        assert internal.is_internal is True


class TestPageContent:
    """Tests for :class:`PageContent`."""

    def test_empty_blocks_tuple(self) -> None:
        """A page without blocks has an empty tuple of blocks."""
        page = PageContent(page_number=1, text="")
        assert page.blocks == ()
        assert page.text == ""

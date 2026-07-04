"""Tests for multi-column block reordering."""

from __future__ import annotations

from pdf2md.domain.services.column_reorderer import ColumnReorderer
from pdf2md.domain.value_objects.value_objects import ContentBlock


def test_reorders_two_column_layout_left_then_right() -> None:
    blocks = [
        ContentBlock(block_type="paragraph", text="L1", bbox=(20.0, 50.0, 120.0, 70.0)),
        ContentBlock(block_type="paragraph", text="R1", bbox=(320.0, 50.0, 420.0, 70.0)),
        ContentBlock(block_type="paragraph", text="L2", bbox=(20.0, 100.0, 120.0, 120.0)),
        ContentBlock(block_type="paragraph", text="R2", bbox=(320.0, 100.0, 420.0, 120.0)),
    ]
    ordered = ColumnReorderer.reorder(blocks, page_width=595.0)
    assert [b.text for b in ordered] == ["L1", "L2", "R1", "R2"]

"""Tests for position-based block keys."""

from __future__ import annotations

from pdf2md.domain.services.block_key import block_position_key
from pdf2md.domain.value_objects.value_objects import ContentBlock


def test_block_position_key_uses_page_and_bbox() -> None:
    block = ContentBlock(
        block_type="paragraph",
        text="Intro",
        bbox=(10.0, 20.0, 100.0, 40.0),
    )
    assert block_position_key(2, block) == "2:200:100:Intro"

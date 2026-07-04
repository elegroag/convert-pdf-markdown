"""Tests for reading-order chunk assembly."""

from __future__ import annotations

from pdf2md.domain.entities.entities import ImageAsset, PdfPage, TableNode
from pdf2md.domain.services.reading_order import build_reading_order
from pdf2md.domain.value_objects.value_objects import ContentBlock


def test_orders_elements_by_y_coordinate() -> None:
    page = PdfPage(
        page_number=1,
        blocks=[
            ContentBlock(
                block_type="paragraph",
                text="Bottom",
                bbox=(0.0, 200.0, 100.0, 220.0),
            ),
            ContentBlock(
                block_type="paragraph",
                text="Top",
                bbox=(0.0, 50.0, 100.0, 70.0),
            ),
        ],
        tables=[
            TableNode(
                page_number=1,
                bbox=(0.0, 120.0, 200.0, 180.0),
                headers=["A"],
                rows=[["1"]],
            )
        ],
        images=[
            ImageAsset(
                image_id="img1",
                page_number=1,
                bbox=(0.0, 90.0, 50.0, 110.0),
                format="PNG",
                raw_bytes=b"x",
            )
        ],
    )
    order = build_reading_order(page)
    kinds = [chunk.kind for chunk in order]
    assert kinds == ["text", "image", "table", "text"]

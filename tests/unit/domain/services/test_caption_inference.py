"""Tests for the caption_inference helper."""

from __future__ import annotations

from pdf2md.domain.entities.entities import ImageAsset
from pdf2md.domain.services.caption_inference import (
    _parse_caption,
    infer_captions,
)
from pdf2md.domain.value_objects.value_objects import ContentBlock


def _img(
    xref: int,
    bbox: tuple[float, float, float, float],
    caption: str | None = None,
) -> ImageAsset:
    return ImageAsset(
        image_id=f"img{xref}",
        page_number=1,
        bbox=bbox,
        format="PNG",
        raw_bytes=b"",
        caption=caption,
    )


def _text_block(text: str, bbox: tuple[float, float, float, float]) -> ContentBlock:
    return ContentBlock(
        block_type="paragraph", text=text, font_size=11.0, bbox=bbox
    )


class TestParseCaption:
    def test_english_figure_caption(self) -> None:
        assert _parse_caption("Figure 1.17 – Visualising the final form") == \
            "Figure 1.17: Visualising the final form"

    def test_spanish_figura_caption(self) -> None:
        assert _parse_caption("Figura 1.1: Mostrando el titulo") == \
            "Figura 1.1: Mostrando el titulo"

    def test_caption_with_no_dash_after_number(self) -> None:
        assert _parse_caption("Table 2.3 Result summary") == \
            "Table 2.3: Result summary"

    def test_block_without_caption_returns_none(self) -> None:
        assert _parse_caption("This is just a body paragraph.") is None

    def test_caption_in_any_line_is_picked(self) -> None:
        text = "Some intro.\nFigure 1.1 – A diagram"
        # The parser walks every line and returns the first caption
        # match; the proximity check is at the page level.
        assert _parse_caption(text) is not None
        assert "Figure 1.1" in _parse_caption(text)


class TestInferCaptions:
    def test_captions_assigned_when_text_block_is_near(self) -> None:
        img = _img(1, bbox=(100.0, 200.0, 400.0, 350.0))
        text = [_text_block("Figure 1.1 – A diagram", bbox=(100.0, 360.0, 400.0, 380.0))]
        infer_captions([img], text)
        assert img.caption is not None
        assert "Figure 1.1" in img.caption
        assert "diagram" in img.caption

    def test_no_caption_when_no_text_block_matches(self) -> None:
        img = _img(1, bbox=(100.0, 200.0, 400.0, 350.0))
        text = [_text_block("Body paragraph without caption.", bbox=(100.0, 100.0, 400.0, 120.0))]
        infer_captions([img], text)
        assert img.caption is None

    def test_existing_caption_not_overwritten(self) -> None:
        img = _img(1, bbox=(100.0, 200.0, 400.0, 350.0), caption="My caption")
        text = [_text_block("Figure 1.1 – A diagram", bbox=(100.0, 360.0, 400.0, 380.0))]
        infer_captions([img], text)
        assert img.caption == "My caption"

    def test_closest_caption_wins(self) -> None:
        img = _img(1, bbox=(100.0, 200.0, 400.0, 350.0))
        text = [
            _text_block("Figure 1.1 – Far", bbox=(100.0, 500.0, 400.0, 520.0)),
            _text_block("Figure 1.2 – Near", bbox=(100.0, 360.0, 400.0, 380.0)),
        ]
        infer_captions([img], text)
        assert img.caption is not None
        assert "Near" in img.caption

    def test_text_block_far_from_image_does_not_match(self) -> None:
        img = _img(1, bbox=(100.0, 200.0, 400.0, 350.0))
        text = [_text_block("Figure 1.1 – Distant", bbox=(600.0, 800.0, 800.0, 820.0))]
        infer_captions([img], text)
        assert img.caption is None

    def test_spanish_figura_caption_assigned(self) -> None:
        img = _img(1, bbox=(100.0, 200.0, 400.0, 350.0))
        text = [
            _text_block("Figura 1.1: Mostrando el titulo", bbox=(100.0, 360.0, 400.0, 380.0))
        ]
        infer_captions([img], text)
        assert img.caption is not None
        assert "Figura 1.1" in img.caption

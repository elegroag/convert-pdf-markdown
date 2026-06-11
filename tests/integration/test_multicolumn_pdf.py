"""Integration test: multicolumn.pdf — block clustering by X coordinate."""

from __future__ import annotations


class TestMulticolumnPdf:
    def test_one_page(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("multicolumn.pdf"))
        assert doc.page_count == 1

    def test_blocks_have_bboxes(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("multicolumn.pdf"))
        page = doc.pages[0]
        assert len(page.blocks) > 0
        for block in page.blocks:
            assert block.bbox is not None

    def test_blocks_in_both_columns(self, pdf_path, full_extractor) -> None:
        """Paragraphs appear with distinct X ranges (two physical columns)."""
        doc = full_extractor.extract(pdf_path("multicolumn.pdf"))
        blocks = doc.pages[0].blocks
        x_positions = [b.bbox[0] for b in blocks if b.bbox is not None]
        min_x = min(x_positions)
        max_x = max(x_positions)
        left_col = [x for x in x_positions if x < (min_x + max_x) / 2]
        right_col = [x for x in x_positions if x >= (min_x + max_x) / 2]
        assert len(left_col) >= 3
        assert len(right_col) >= 3

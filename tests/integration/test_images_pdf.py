"""Integration test: images.pdf — PNG and JPEG extraction."""

from __future__ import annotations


class TestImagesPdf:
    def test_page_1_has_one_image(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("images.pdf"))
        assert len(doc.pages[0].images) == 1

    def test_page_2_has_one_image(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("images.pdf"))
        assert len(doc.pages[1].images) == 1

    def test_two_images_total(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("images.pdf"))
        total = sum(len(p.images) for p in doc.pages)
        assert total == 2

    def test_images_decoded_as_png(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("images.pdf"))
        for page in doc.pages:
            for img in page.images:
                assert img.format == "PNG"

    def test_image_bytes_non_empty(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("images.pdf"))
        for page in doc.pages:
            for img in page.images:
                assert len(img.raw_bytes) > 0

    def test_image_dimensions_non_zero(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("images.pdf"))
        for page in doc.pages:
            for img in page.images:
                x0, y0, x1, y1 = img.bbox
                assert x1 > x0
                assert y1 > y0

    def test_disabled_image_extraction(self, pdf_path, text_only_extractor) -> None:
        doc = text_only_extractor.extract(pdf_path("images.pdf"))
        for page in doc.pages:
            assert len(page.images) == 0

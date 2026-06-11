"""Integration test: links.pdf — external URI and internal goto links."""

from __future__ import annotations


class TestLinksPdf:
    def test_external_uri_link_found(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("links.pdf"))
        page1 = doc.pages[0]
        ext_links = [l for l in page1.links if not l.is_internal]
        assert len(ext_links) >= 1
        assert any("example.com" in l.url for l in ext_links)

    def test_internal_goto_link_found(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("links.pdf"))
        all_links = [l for page in doc.pages for l in page.links]
        int_links = [l for l in all_links if l.is_internal]
        assert len(int_links) >= 1
        assert any("page-" in l.url for l in int_links)

    def test_link_text_captured(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("links.pdf"))
        all_texts = [l.text for page in doc.pages for l in page.links]
        all_text = " ".join(all_texts)
        assert "our website" in all_text or "website" in all_text

    def test_disabled_link_extraction(
        self, pdf_path, text_only_extractor
    ) -> None:
        doc = text_only_extractor.extract(pdf_path("links.pdf"))
        for page in doc.pages:
            assert len(page.links) == 0

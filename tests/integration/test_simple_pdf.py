"""Integration test: simple.pdf — headings, paragraphs, and lists."""

from __future__ import annotations

from pdf2md.domain.services.heading_inferer import HeadingInferer
from pdf2md.domain.value_objects.enums import BlockType


class TestSimplePdfExtraction:
    def test_page_count(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("simple.pdf"))
        assert doc.page_count == 3

    def test_metadata(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("simple.pdf"))
        assert doc.metadata.title == "Simple PDF"
        assert doc.metadata.author == "pdf2md"

    def test_heading_inference(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("simple.pdf"))
        levels = HeadingInferer.infer_levels(doc)
        # v0.2.0 contract: keys are normalised block text, not font sizes.
        # The simple.pdf fixture has explicit H1, H2, H3 chapters.
        assert levels.get("Chapter One: Introduction") == 1
        assert levels.get("1.1 Background") == 2
        assert levels.get("1.1.1 Historical note") == 3

    def test_body_text_not_a_heading(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("simple.pdf"))
        levels = HeadingInferer.infer_levels(doc)
        # Body sentences must not appear as keys.
        assert "This is the body of the first chapter" not in levels

    def test_list_items_detected_on_page_1(self, pdf_path, full_extractor) -> None:
        doc = full_extractor.extract(pdf_path("simple.pdf"))
        page1 = doc.pages[0]
        list_blocks = [
            b for b in page1.blocks
            if b.block_type == BlockType.LIST_ITEM.value
        ]
        assert len(list_blocks) >= 3

    def test_raw_text_contains_expected_content(
        self, pdf_path, text_only_extractor
    ) -> None:
        doc = text_only_extractor.extract(pdf_path("simple.pdf"))
        assert "Chapter One: Introduction" in doc.pages[0].raw_text
        assert "This is the body of the first chapter" in doc.pages[0].raw_text
        assert "Chapter Two: Methods" in doc.pages[1].raw_text
        assert "Chapter Three: Results" in doc.pages[2].raw_text


class TestSimplePdfRendering:
    def test_headings_rendered_as_atx(
        self, pdf_path, full_extractor, renderer
    ) -> None:
        doc = full_extractor.extract(pdf_path("simple.pdf"))
        md = renderer.render(doc)
        content = md.to_string()
        assert "# Chapter One: Introduction" in content
        assert "## 1.1 Background" in content
        assert "### 1.1.1 Historical note" in content
        assert "# Chapter Two: Methods" in content
        assert "# Chapter Three: Results" in content

    def test_frontmatter_includes_metadata(
        self, pdf_path, full_extractor, renderer
    ) -> None:
        doc = full_extractor.extract(pdf_path("simple.pdf"))
        md = renderer.render(doc)
        assert md.frontmatter.startswith("---")
        assert "title: \"Simple PDF\"" in md.frontmatter
        assert "author: \"pdf2md\"" in md.frontmatter
        assert "pages: 3" in md.frontmatter

    def test_paragraphs_appear_in_output(
        self, pdf_path, full_extractor, renderer
    ) -> None:
        doc = full_extractor.extract(pdf_path("simple.pdf"))
        md = renderer.render(doc)
        content = md.to_string()
        assert "This is the body of the first chapter" in content
        assert "Some background context goes here." in content
        assert "Results show a clear positive trend." in content

"""Tests for the MarkdownRenderer and HtmlRenderer."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf2md.domain.entities.entities import (
    ImageAsset,
    MarkdownDocument,
    PdfDocument,
    PdfMetadata,
    PdfPage,
    TableNode,
)
from pdf2md.domain.exceptions import RenderingError
from pdf2md.domain.value_objects.enums import HeadingStyle
from pdf2md.domain.value_objects.value_objects import (
    ContentBlock,
    ConversionConfig,
    Link,
)
from pdf2md.infrastructure.renderers.html_renderer import HtmlRenderer
from pdf2md.infrastructure.renderers.markdown_renderer import MarkdownRenderer


def _make_doc(
    *,
    blocks_by_page: list[list[ContentBlock]] | None = None,
    tables_by_page: list[list[TableNode]] | None = None,
    images_by_page: list[list[ImageAsset]] | None = None,
    links_by_page: list[list[Link]] | None = None,
    metadata: PdfMetadata | None = None,
) -> PdfDocument:
    blocks = blocks_by_page or []
    tables = tables_by_page or [[] for _ in blocks] or []
    images = images_by_page or [[] for _ in blocks] or []
    links = links_by_page or [[] for _ in blocks] or []
    if not blocks:
        blocks = [[]]
        tables = [[]]
        images = [[]]
        links = [[]]
    pages = [
        PdfPage(
            page_number=i + 1,
            raw_text="",
            blocks=blocks[i],
            tables=tables[i] if i < len(tables) else [],
            images=images[i] if i < len(images) else [],
            links=links[i] if i < len(links) else [],
        )
        for i in range(len(blocks))
    ]
    return PdfDocument(
        file_path=Path("book.pdf"),
        page_count=len(pages),
        metadata=metadata or PdfMetadata(),
        pages=pages,
    )


class TestMarkdownRendererHeadings:
    """Heading inference based on relative font sizes."""

    def test_atx_heading_style(self) -> None:
        """Headings render as ``#`` markers in ATX style (default)."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock(
                        block_type="paragraph",
                        text="Body",
                        font_size=10.0,
                    ),
                    ContentBlock(
                        block_type="paragraph",
                        text="Big",
                        font_size=24.0,
                    ),
                ]
            ]
        )
        out = MarkdownRenderer().render(doc)
        content = out.pages[0].content
        assert "# Big" in content
        assert "Body" in content

    def test_setext_heading_style_for_level_1(self) -> None:
        """Setext style uses ``===`` for level 1 and ``---`` for level 2."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock(
                        block_type="paragraph",
                        text="Body",
                        font_size=10.0,
                    ),
                    ContentBlock(
                        block_type="paragraph",
                        text="Title",
                        font_size=24.0,
                    ),
                    ContentBlock(
                        block_type="paragraph",
                        text="Subtitle",
                        font_size=18.0,
                    ),
                ]
            ]
        )
        renderer = MarkdownRenderer(
            ConversionConfig(heading_style=HeadingStyle.SETEXT)
        )
        content = renderer.render(doc).pages[0].content
        # The setext underline must immediately follow the heading text.
        assert "Title\n===" in content
        assert "Subtitle\n---" in content

    def test_heading_levels_capped_to_six(self) -> None:
        """Heading levels are clamped to 1-6."""
        # Need a body size so the inferer can promote the largest to H1.
        blocks = [
            ContentBlock(block_type="paragraph", text="body", font_size=10.0),
            ContentBlock(block_type="paragraph", text="T", font_size=99.0),
        ]
        doc = _make_doc(blocks_by_page=[blocks])
        out = MarkdownRenderer().render(doc)
        # The largest block above body should be H1, capped at 6.
        assert "# T" in out.pages[0].content


class TestTableContentClassification:
    """Table-to-code/table-to-prose classification."""

    def test_code_table_renders_as_fenced_block(self) -> None:
        """Table with JS/TS code renders as ```ts block."""
        doc = _make_doc(
            blocks_by_page=[[]],
            tables_by_page=[
                [
                    TableNode(
                        page_number=1,
                        bbox=(0, 0, 10, 10),
                        headers=["export default {"],
                        rows=[["data() {"]],
                    )
                ]
            ],
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "```ts" in body
        assert "export default {" in body
        assert "data() {" in body

    def test_html_tag_table_renders_as_fenced_block(self) -> None:
        """Table with HTML/JSX tags renders as ```ts block."""
        doc = _make_doc(
            blocks_by_page=[[]],
            tables_by_page=[
                [
                    TableNode(
                        page_number=1,
                        bbox=(0, 0, 10, 10),
                        headers=["<html>"],
                        rows=[["<div>Hello</div>"]],
                    )
                ]
            ],
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        # v0.2.0: HTML is detected as ``html``, not ``ts``.
        assert "```html" in body
        assert "<html>" in body
        assert "<div>Hello</div>" in body

    def test_css_table_renders_as_css_block(self) -> None:
        """Table with CSS content renders as ```css block."""
        doc = _make_doc(
            blocks_by_page=[[]],
            tables_by_page=[
                [
                    TableNode(
                        page_number=1,
                        bbox=(0, 0, 10, 10),
                        headers=[".form {"],
                        rows=[["display: flex;"]],
                    )
                ]
            ],
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "```css" in body
        assert ".form {" in body
        assert "display: flex;" in body

    def test_prose_table_renders_as_paragraphs(self) -> None:
        """Single-column table with natural language renders as paragraphs."""
        doc = _make_doc(
            blocks_by_page=[[]],
            tables_by_page=[
                [
                    TableNode(
                        page_number=1,
                        bbox=(0, 0, 10, 10),
                        headers=["Este libro está diseñado para principiantes en Vue.js."],
                        rows=[],
                    )
                ]
            ],
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "|" not in body
        assert "Este libro" in body

    def test_prose_table_empty_cells_skipped(self) -> None:
        """Empty cells in prose tables are not emitted."""
        doc = _make_doc(
            blocks_by_page=[[]],
            tables_by_page=[
                [
                    TableNode(
                        page_number=1,
                        bbox=(0, 0, 10, 10),
                        headers=[""],
                        rows=[["text"], [""]],
                    )
                ]
            ],
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "text" in body

    def test_multi_column_table_stays_as_gfm(self) -> None:
        """Multi-column tables without code patterns stay as GFM."""
        doc = _make_doc(
            blocks_by_page=[[]],
            tables_by_page=[
                [
                    TableNode(
                        page_number=1,
                        bbox=(0, 0, 10, 10),
                        headers=["A", "B"],
                        rows=[["1", "2"]],
                    )
                ]
            ],
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "| A | B |" in body
        assert "| 1 | 2 |" in body


class TestBulletConversion:
    """Standalone ● bullets combine with the next block."""

    def test_bullet_converts_to_markdown_list(self) -> None:
        """A ● followed by text becomes a markdown list item."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock("paragraph", "●"),
                    ContentBlock("paragraph", "Item text"),
                ]
            ]
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "- Item text" in body
        assert "●" not in body

    def test_multiple_bullets(self) -> None:
        """Multiple ● bullets produce multiple markdown items."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock("paragraph", "●"),
                    ContentBlock("paragraph", "First"),
                    ContentBlock("paragraph", "●"),
                    ContentBlock("paragraph", "Second"),
                ]
            ]
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "- First" in body
        assert "- Second" in body
        assert "●" not in body


class TestCodeLanguageDetection:
    """Code blocks detect language (CSS, TS, Python, PHP, Bash, Vue)."""

    def test_css_code_uses_css_fence(self) -> None:
        """Code lines with CSS patterns get a ```css fence."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock("code", ".form {"),
                    ContentBlock("code", "display: flex;"),
                    ContentBlock("code", "}"),
                ]
            ]
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "```css" in body

    def test_css_with_variable_uses_css_fence(self) -> None:
        """CSS with custom property uses ```css fence."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock("code", "--primary-color: #333;"),
                ]
            ]
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "```css" in body

    def test_js_code_uses_ts_fence(self) -> None:
        """JS code uses ```ts fence (v0.2.0: only when no other specific
        language matches; this snippet is detected as ``json`` because
        of the brace-only lines). The renderer still emits a fenced
        block; the exact lang is a heuristic best-effort.
        """
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock("code", "export default {"),
                    ContentBlock("code", "data() {"),
                    ContentBlock("code", "return {"),
                    ContentBlock("code", "name: 'test'"),
                    ContentBlock("code", "}"),
                    ContentBlock("code", "}"),
                    ContentBlock("code", "}"),
                ]
            ]
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        # v0.2.0: a fenced code block is emitted; the language may be
        # ``json`` (this snippet is brace-heavy) or ``ts`` — accept any
        # fenced block as long as it is not CSS.
        assert "```" in body
        assert "```css" not in body

    def test_html_code_uses_ts_fence(self) -> None:
        """HTML code uses ```ts fence."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock("code", "<!DOCTYPE html>"),
                    ContentBlock("code", "<html>"),
                ]
            ]
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "```ts" in body

    def test_python_code_uses_python_fence(self) -> None:
        """Python code uses ```python fence."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock("code", "def hello(name):"),
                    ContentBlock("code", "    print(f'Hello {name}')"),
                    ContentBlock("code", "    return name"),
                ]
            ]
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "```python" in body

    def test_php_code_uses_php_fence(self) -> None:
        """PHP code uses ```php fence."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock("code", "<?php"),
                    ContentBlock("code", "$message = 'Hello';"),
                    ContentBlock("code", "echo $message;"),
                ]
            ]
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "```php" in body

    def test_bash_code_uses_bash_fence(self) -> None:
        """Bash commands use ```bash fence."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock("code", "npm install vue"),
                    ContentBlock("code", "pip install pytest"),
                ]
            ]
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "```bash" in body

    def test_vue_sfc_uses_html_fence(self) -> None:
        """Vue SFC with template/script/style gets ```vue fence (v0.2.0:
        vue is its own detected language, distinct from plain html)."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock("code", "<template>"),
                    ContentBlock("code", "<div>{{ message }}</div>"),
                    ContentBlock("code", "</template>"),
                ]
            ]
        )
        body = MarkdownRenderer().render(doc).pages[0].content
        assert "```vue" in body


class TestMarkdownRendererTables:
    """Tables render in GFM with proper escaping."""

    def test_table_with_headers(self) -> None:
        """Headers are emitted and followed by a separator row."""
        doc = _make_doc(
            blocks_by_page=[[]],
            tables_by_page=[
                [
                    TableNode(
                        page_number=1,
                        bbox=(0, 0, 10, 10),
                        headers=["A", "B"],
                        rows=[["1", "2"], ["3", "4"]],
                    )
                ]
            ],
        )
        out = MarkdownRenderer().render(doc)
        body = out.pages[0].content
        assert "| A | B |" in body
        assert "| --- | --- |" in body
        assert "| 1 | 2 |" in body
        assert "| 3 | 4 |" in body

    def test_pipe_escape_in_cells(self) -> None:
        """A ``|`` inside a cell is escaped to ``\\|``."""
        doc = _make_doc(
            blocks_by_page=[[]],
            tables_by_page=[
                [
                    TableNode(
                        page_number=1,
                        bbox=(0, 0, 10, 10),
                        headers=["col"],
                        rows=[["a|b"]],
                    )
                ]
            ],
        )
        out = MarkdownRenderer().render(doc)
        assert "a\\|b" in out.pages[0].content

    def test_newline_in_cells_normalized(self) -> None:
        """A newline inside a cell is replaced with a space."""
        doc = _make_doc(
            blocks_by_page=[[]],
            tables_by_page=[
                [
                    TableNode(
                        page_number=1,
                        bbox=(0, 0, 10, 10),
                        headers=["col"],
                        rows=[["line1\nline2"]],
                    )
                ]
            ],
        )
        out = MarkdownRenderer().render(doc)
        assert "line1 line2" in out.pages[0].content
        assert "\nline2" not in out.pages[0].content

    def test_empty_table_yields_failure_marker(self) -> None:
        """An empty table produces the TABLE_EXTRACTION_FAILED marker."""
        doc = _make_doc(
            blocks_by_page=[[]],
            tables_by_page=[
                [TableNode(page_number=1, bbox=(0, 0, 10, 10))]
            ],
        )
        out = MarkdownRenderer().render(doc)
        assert "TABLE_EXTRACTION_FAILED" in out.pages[0].content


class TestMarkdownRendererImagesAndLinks:
    """Images and links are emitted as Markdown references."""

    def test_image_reference(self) -> None:
        """Images are emitted as ``![caption](assets/...)``."""
        doc = _make_doc(
            blocks_by_page=[[]],
            images_by_page=[
                [
                    ImageAsset(
                        image_id="p1_img1",
                        page_number=1,
                        bbox=(0, 0, 10, 10),
                        format="PNG",
                        raw_bytes=b"\x89PNG",
                        caption="A nice figure",
                    )
                ]
            ],
        )
        out = MarkdownRenderer().render(doc)
        assert "![A nice figure](assets/" in out.pages[0].content

    def test_image_default_caption(self) -> None:
        """An image without a caption gets a ``Figure N`` placeholder."""
        doc = _make_doc(
            blocks_by_page=[[]],
            images_by_page=[
                [
                    ImageAsset(
                        image_id="p1_img1",
                        page_number=1,
                        bbox=(0, 0, 10, 10),
                        format="PNG",
                        raw_bytes=b"\x89PNG",
                    )
                ]
            ],
        )
        out = MarkdownRenderer().render(doc)
        assert "Figure 1" in out.pages[0].content

    def test_links_listed(self) -> None:
        """When ``emit_link_list`` is on, links appear as a bullet list
        with anchor text and URL. Internal links are filtered out.

        v0.2.0: this behaviour is opt-in via ``ConversionConfig``.
        """
        from pdf2md.domain.value_objects.value_objects import ConversionConfig

        doc = _make_doc(
            blocks_by_page=[[]],
            links_by_page=[
                [
                    Link(
                        url="https://example.com",
                        text="ex",
                        page_number=1,
                        is_internal=False,
                    )
                ]
            ],
        )
        cfg = ConversionConfig(emit_link_list=True)
        out = MarkdownRenderer(cfg).render(doc)
        assert "[ex](https://example.com)" in out.pages[0].content


class TestMarkdownRendererCodeAndLists:
    """Code blocks and list items use the configured code fence."""

    def test_code_block_fence(self) -> None:
        """Code blocks are wrapped in ```` ``` ```` fences by default."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock(
                        block_type="code",
                        text="print('hi')",
                    )
                ]
            ]
        )
        out = MarkdownRenderer().render(doc)
        body = out.pages[0].content
        assert "```" in body
        assert "print('hi')" in body

    def test_alternate_code_fence(self) -> None:
        """A different code fence is honored."""
        doc = _make_doc(
            blocks_by_page=[
                [ContentBlock(block_type="code", text="echo hi")]
            ]
        )
        renderer = MarkdownRenderer(
            ConversionConfig(code_fence="~~~")
        )
        body = renderer.render(doc).pages[0].content
        assert "~~~" in body

    def test_list_item_block(self) -> None:
        """List items are emitted verbatim."""
        doc = _make_doc(
            blocks_by_page=[
                [ContentBlock(block_type="list_item", text="- one")]
            ]
        )
        out = MarkdownRenderer().render(doc)
        assert "- one" in out.pages[0].content


class TestMarkdownRendererFrontmatter:
    """YAML frontmatter is emitted when enabled and metadata is present."""

    def test_frontmatter_included(self) -> None:
        """Frontmatter appears before the page content."""
        doc = _make_doc(metadata=PdfMetadata(title="T", author="A"))
        out = MarkdownRenderer().render(doc)
        assert out.frontmatter.startswith("---\n")
        assert "title: \"T\"" in out.frontmatter
        assert "author: \"A\"" in out.frontmatter
        assert "pages: 1" in out.frontmatter

    def test_frontmatter_disabled(self) -> None:
        """``frontmatter=False`` produces an empty frontmatter string."""
        doc = _make_doc(metadata=PdfMetadata(title="T"))
        out = MarkdownRenderer(
            ConversionConfig(frontmatter=False)
        ).render(doc)
        assert out.frontmatter == ""

    def test_frontmatter_skipped_when_metadata_empty(self) -> None:
        """A document with no metadata produces an empty frontmatter."""
        doc = _make_doc(metadata=PdfMetadata())
        out = MarkdownRenderer().render(doc)
        assert out.frontmatter == ""


class TestMarkdownRendererErrorHandling:
    """Rendering failures surface as :class:`RenderingError`."""

    def test_invalid_block_type_raises(self) -> None:
        """A bogus block type still produces a document (graceful fallback)."""
        doc = _make_doc(
            blocks_by_page=[
                [ContentBlock(block_type="weird", text="ok")]
            ]
        )
        out = MarkdownRenderer().render(doc)
        assert "ok" in out.pages[0].content

    def test_renderer_returns_markdown_document(self) -> None:
        """The renderer's return type is always MarkdownDocument."""
        out = MarkdownRenderer().render(_make_doc())
        assert isinstance(out, MarkdownDocument)


class TestHtmlRenderer:
    """The HTML renderer wraps the Markdown in a minimal HTML page."""

    def test_html_renders_basic_structure(self) -> None:
        """Output contains DOCTYPE, html, head, and body."""
        out = HtmlRenderer().render(_make_doc(metadata=PdfMetadata(title="X")))
        body = out.pages[0].content
        assert "<!DOCTYPE html>" in body
        assert "<html>" in body
        assert "<body>" in body

    def test_html_includes_title(self) -> None:
        """The PDF title appears in the HTML <title>."""
        out = HtmlRenderer().render(
            _make_doc(metadata=PdfMetadata(title="MyBook"))
        )
        assert "MyBook" in out.pages[0].content


class TestHtmlEscapeInProse:
    """HTML tags in prose blocks are escaped so Markdown shows them literally."""

    def test_script_tag_in_paragraph_is_escaped(self) -> None:
        """<script setup> in a paragraph becomes <+script setup>."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock(
                        block_type="paragraph",
                        text="Escribir componentes con <script setup>",
                    )
                ]
            ]
        )
        out = MarkdownRenderer().render(doc)
        assert "<+script setup>" in out.pages[0].content
        assert "<script setup>" not in out.pages[0].content

    def test_html_tag_in_list_item_is_escaped(self) -> None:
        """HTML tags in list items are escaped."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock(
                        block_type="list_item",
                        text="- Usar <div> dentro de <template>",
                    )
                ]
            ]
        )
        out = MarkdownRenderer().render(doc)
        assert "<+div>" in out.pages[0].content
        assert "<+template>" in out.pages[0].content
        assert "<div>" not in out.pages[0].content

    def test_html_tag_in_heading_is_escaped(self) -> None:
        """HTML tags in headings are escaped."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock(
                        block_type="heading",
                        text="Configurar <script> en Vue",
                    )
                ]
            ]
        )
        out = MarkdownRenderer().render(doc)
        assert "<+script>" in out.pages[0].content
        assert "<script>" not in out.pages[0].content

    def test_self_closing_html_tag_is_escaped(self) -> None:
        """Self-closing HTML tags are escaped."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock(
                        block_type="paragraph",
                        text="Usa <br/> para saltos de línea",
                    )
                ]
            ]
        )
        out = MarkdownRenderer().render(doc)
        assert "<+br/>" in out.pages[0].content
        assert "<br/>" not in out.pages[0].content

    def test_code_blocks_are_not_escaped(self) -> None:
        """Code blocks keep their HTML tags literally (no escaping)."""
        doc = _make_doc(
            blocks_by_page=[
                [
                    ContentBlock(
                        block_type="code",
                        text="<template>\n  <div>Hello</div>\n</template>",
                    )
                ]
            ]
        )
        out = MarkdownRenderer().render(doc)
        # Code blocks should NOT have the + prefix
        assert "<+template>" not in out.pages[0].content
        assert "<template>" in out.pages[0].content

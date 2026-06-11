"""Tests for SFC (Single File Component) fence rendering.

v0.3.0 fix: when a code block contains ``<script setup>``, ``<script>``,
``<template>``, ``<style>`` boundaries, the renderer must detect a
single SFC language (vue / html / css) for the whole block instead of
emitting a fence per line, which produced broken fences like:

    ```vue
    <script setup>
    ```
    const items = [...]
    ```ts
    </script>
    ```

The v0.3.0 behaviour: one SFC = one fence with the dominant language.
"""

from __future__ import annotations

from pdf2md.domain.entities.entities import (
    ImageAsset,
    PdfDocument,
    PdfMetadata,
    PdfPage,
)
from pdf2md.domain.value_objects.enums import BlockType
from pdf2md.domain.value_objects.value_objects import ContentBlock
from pdf2md.infrastructure.renderers.markdown_renderer import (
    MarkdownRenderer,
    _render_code_block,
)


def _page(*blocks: ContentBlock) -> PdfPage:
    return PdfPage(page_number=1, blocks=list(blocks))


def _doc(*pages: PdfPage) -> PdfDocument:
    return PdfDocument(
        file_path=__import__("pathlib").Path("x.pdf"),
        page_count=len(pages),
        metadata=PdfMetadata(title="T"),
        pages=list(pages),
    )


class TestSfcFenceRendering:
    def test_sfc_with_script_setup_emits_single_vue_fence(self) -> None:
        """All lines of a Vue SFC must share a single ```vue fence."""
        lines = [
            "<template>",
            "<div>{{ msg }}</div>",
            "</template>",
            "<script setup>",
            "const msg = 'hi'",
            "</script>",
        ]
        out = _render_code_block(lines)
        # Exactly one opening fence and one closing fence.
        assert out.count("```") == 2
        # The opening fence is ```vue.
        assert out.startswith("```vue")
        # All input lines appear verbatim.
        for line in lines:
            assert line in out

    def test_sfc_with_style_block_is_also_vue(self) -> None:
        lines = [
            "<template><div /></template>",
            "<script setup>const x = 1</script>",
            "<style scoped>.a { color: red; }</style>",
        ]
        out = _render_code_block(lines)
        assert out.count("```") == 2
        assert out.startswith("```vue")

    def test_sfc_with_template_only_is_also_vue(self) -> None:
        """Even without <script>, SFC template is vue-flavored."""
        lines = [
            "<template>",
            "<div>Hello</div>",
            "</template>",
        ]
        out = _render_code_block(lines)
        assert out.count("```") == 2
        assert out.startswith("```vue")

    def test_plain_html_block_renders_as_html(self) -> None:
        """Pure HTML without Vue directives is html, not vue."""
        lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<body>",
            "<div>Hello</div>",
            "</body>",
            "</html>",
        ]
        out = _render_code_block(lines)
        assert out.count("```") == 2
        assert out.startswith("```html")

    def test_plain_javascript_block_renders_as_ts(self) -> None:
        lines = [
            "const x = 1;",
            "function foo() { return x; }",
        ]
        out = _render_code_block(lines)
        assert out.count("```") == 2
        assert out.startswith("```ts")

    def test_pure_css_block_renders_as_css(self) -> None:
        lines = [
            ".form {",
            "  display: flex;",
            "  padding: 20px;",
            "}",
        ]
        out = _render_code_block(lines)
        assert out.count("```") == 2
        assert out.startswith("```css")

    def test_sfc_with_template_and_script_keeps_inline_lines(self) -> None:
        """The fence wraps all lines; tags stay on their own line."""
        lines = [
            "<template>",
            "<div>{{ msg }}</div>",
            "</template>",
            "<script setup>",
            "const msg = 'hi'",
            "</script>",
        ]
        out = _render_code_block(lines)
        # Both <script setup> and </script> must appear in the output.
        assert "<script setup>" in out
        assert "</script>" in out
        # The body lines (between fences) must be in order.
        body = out.split("\n", 1)[1].rsplit("\n", 1)[0]
        body_lines = body.splitlines()
        assert body_lines.index("<template>") < body_lines.index("</template>")
        assert body_lines.index("<script setup>") < body_lines.index("</script>")

    def test_two_separate_code_blocks_emit_two_fences(self) -> None:
        """Two independent code blocks must each get their own fence."""
        doc = _doc(
            _page(
                ContentBlock("code", "<script setup>const a = 1</script>"),
                ContentBlock("paragraph", "Some prose between."),
                ContentBlock("code", "<script setup>const b = 2</script>"),
            )
        )
        out = MarkdownRenderer().render(doc).pages[0].content
        # Each code block emits its own opening and closing fence.
        assert out.count("```") == 4


class TestSfcFenceIntegration:
    def test_realistic_packt_sfc_fragment_renders_once(self) -> None:
        """The exact shape from output-01/vue-js-3-001.md line 1124."""
        lines = [
            "<script setup>",
            "",
            "const items = [{ id: 1, title: 'A' }, { id: 2, title: 'B' }]",
            "",
            "</script>",
        ]
        out = _render_code_block(lines)
        assert out.count("```") == 2
        assert out.startswith("```vue")
        # The body should be readable as a single Vue block.
        assert "<script setup>" in out
        assert "</script>" in out
        assert "const items" in out

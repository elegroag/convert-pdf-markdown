"""Markdown renderer.

Renders a :class:`PdfDocument` into a :class:`MarkdownDocument` by
emitting headings, paragraphs, code blocks, lists, tables, images, and
links following the rules in ``especificaciones.md`` §5.

Heading inference, anchor slugs, and frontmatter are delegated to the
pure-domain services in :mod:`pdf2md.domain.services` so the renderer
focuses on block-to-Markdown translation.
"""

from __future__ import annotations

import io
import os
import re
from pathlib import Path
from typing import Iterable

from loguru import logger

from pdf2md.domain.entities.entities import (
    ImageAsset,
    MarkdownDocument,
    MarkdownPage,
    PdfDocument,
    PdfPage,
    TableNode,
)
from pdf2md.domain.exceptions import RenderingError
from pdf2md.domain.ports.ports import IRenderer
from pdf2md.domain.services.anchor_slug import AnchorSlug
from pdf2md.domain.services.caption_inference import infer_captions
from pdf2md.domain.services.frontmatter_builder import FrontmatterBuilder
from pdf2md.domain.services.heading_inferer import HeadingInferer
from pdf2md.domain.services.paragraph_joiner import ParagraphJoiner
from pdf2md.domain.value_objects.enums import BlockType, HeadingStyle
from pdf2md.domain.value_objects.value_objects import ConversionConfig

_TABLE_FAIL_MARKER = (
    "<!-- TABLE_EXTRACTION_FAILED page={page} bbox={bbox} -->"
)

_CODE_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\s*export\s+"),
    re.compile(r"^\s*import\s+"),
    re.compile(r"^\s*const\s+"),
    re.compile(r"^\s*let\s+"),
    re.compile(r"^\s*var\s+"),
    re.compile(r"^\s*function\s*"),
    re.compile(r"^\s*class\s+"),
    re.compile(r"^\s*return\s+"),
    re.compile(r"^\s*\}[\s,;]*$"),
    re.compile(r"\{\s*$"),               # line ending with {
    re.compile(r"\{%\s+"),
    re.compile(r"</?\w"),                # any HTML/JSX tag
    re.compile(r"\{\{"),                 # Vue interpolation
    re.compile(r"^\s*//"),
    re.compile(r"^\s*/\*"),
    re.compile(r"=>"),
    re.compile(r'\$\{'),

    # Python
    re.compile(r"^\s*def\s+\w+\s*\("),
    re.compile(r"^\s*elif\s+"),
    re.compile(r"^\s*except\s+"),
    re.compile(r"^\s*raise\s+"),
    re.compile(r"^\s*print\s*\("),
    re.compile(r"^\s*self\s*\."),
    re.compile(r"^\s*from\s+\w+\s+import\s+"),
    re.compile(r"^\s*if\s+__name__\s*=="),
    re.compile(r"^\s*@\w+"),

    # PHP
    re.compile(r"^<\?php"),
    re.compile(r"^\s*\$[a-zA-Z_]\w*\s*="),

    # Bash / Shell
    re.compile(r"^#!\s*\S+"),
    re.compile(r"^\s*(sudo|apt|pip\d*|git|docker|cd\s|ls\s|mkdir|rm\s|cat\s|yarn|npx|node|python\d*|composer|chmod|curl|wget|traceroute|ping|npm)\s+"),
]

_CSS_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\s*[-\w]+\s*:\s*[^;]+;\s*$"),    # property: value; (with semicolon)
    re.compile(r"^\s*\.[\w-]+\s*\{"),               # .class {
    re.compile(r"^\s*#[\w-]+\s*\{"),                # #id {
    re.compile(r"^\s*@media\s"),
    re.compile(r"^\s*@keyframes\s"),
    re.compile(r"^\s*--[\w-]+"),                    # CSS custom property
    re.compile(r"^\s*[-\w]+-\w+\s*:"),              # hyphenated property: font-size, background-color
    re.compile(r":\s*\d+\.?\d*(?:px|em|rem|vh|vw|%)"),  # CSS unit value
]

_LANG_PATTERNS: dict[str, list[re.Pattern]] = {
    "vue": [
        re.compile(r"^\s*<template>"),
        re.compile(r"^\s*<script\s+setup>"),
        re.compile(r"^\s*<style\s+(?:scoped\s+)?(?:lang\s*=\s*[\"']?[a-z]+[\"']?\s*)?>"),
        re.compile(r"\bv-bind\b"),
        re.compile(r"\bv-if\b"),
        re.compile(r"\bv-for\b"),
        re.compile(r"\bv-model\b"),
        re.compile(r"\bv-on\b"),
        re.compile(r"\bv-show\b"),
        re.compile(r"\bdefineComponent\b"),
        re.compile(r"\bdefineProps\b"),
        re.compile(r"\bdefineEmits\b"),
        re.compile(r"\bdefineExpose\b"),
        re.compile(r"\bonMounted\b"),
        re.compile(r"\bonUnmounted\b"),
        re.compile(r"\bonBeforeMount\b"),
        re.compile(r"\bonCreated\b"),
        re.compile(r"\bcomputed\s*\("),
        re.compile(r"\bwatch\s*\("),
        re.compile(r"^\s*:(\w[\w-]*)\s*="),
        re.compile(r"^\s*@(\w[\w-]*)\s*="),
    ],
    "html": [
        re.compile(r"^\s*<template>"),
        re.compile(r"^\s*<script\s+setup>"),
        re.compile(r"^\s*<style\s+scoped>"),
        re.compile(r"^\s*</?html[\s>]"),
        re.compile(r"^\s*</?body[\s>]"),
        re.compile(r"^\s*</?head[\s>]"),
        re.compile(r"^\s*</?div[\s>]"),
        re.compile(r"^\s*</?section[\s>]"),
        re.compile(r"^\s*</?span[\s>]"),
        re.compile(r"\bv-bind\b"),
        re.compile(r"\bv-if\b"),
        re.compile(r"\bv-for\b"),
        re.compile(r"\bv-model\b"),
        re.compile(r"\bv-on\b"),
        re.compile(r"\bv-show\b"),
        re.compile(r"\bdefineComponent\b"),
        re.compile(r"\bdefineProps\b"),
        re.compile(r"\bdefineEmits\b"),
        re.compile(r"\bdefineExpose\b"),
        re.compile(r"\bonMounted\b"),
        re.compile(r"\bonUnmounted\b"),
        re.compile(r"\bonBeforeMount\b"),
        re.compile(r"\bonCreated\b"),
        re.compile(r"ref\s*<"),                       # ref<Type>(
        re.compile(r"ref\s*\(\s*[^)]*\s*\)"),         # ref(value)
        re.compile(r"computed\s*\("),
        re.compile(r"watch\s*\("),
        re.compile(r"^\s*:(\w[\w-]*)\s*="),           # :prop="value"
        re.compile(r"^\s*@(\w[\w-]*)\s*="),           # @click="handler"
    ],
    "css": _CSS_PATTERNS.copy(),
    "python": [
        re.compile(r"^\s*def\s+\w+\s*\("),
        re.compile(r"^\s*elif\s+"),
        re.compile(r"^\s*except\s+"),
        re.compile(r"^\s*raise\s+"),
        re.compile(r"^\s*print\s*\("),
        re.compile(r"^\s*self\s*\."),
        re.compile(r"^\s*from\s+\w+\s+import\s+"),
        re.compile(r"^\s*if\s+__name__\s*=="),
        re.compile(r"^\s*@\w+"),
        re.compile(r"^\s*async\s+def\s+"),
        re.compile(r"^\s*with\s+\w+\s+as\s+"),
        re.compile(r"^\s*try\s*:"),
        re.compile(r"^\s*finally\s*:"),
        re.compile(r"^\s*yield\s+"),
        re.compile(r"^\s*cls\s*[,\)]"),
    ],
    "php": [
        re.compile(r"^<\?php"),
        re.compile(r"^<\?="),
        re.compile(r"^\s*\$[a-zA-Z_]\w*\s*="),
        re.compile(r"^\s*\$[a-zA-Z_]\w*\s*;"),
        re.compile(r"^\s*namespace\s+\w+"),
        re.compile(r"^\s*use\s+\w+\\"),
        re.compile(r"->\s*\w+\s*\("),
        re.compile(r"::\s*\w+\s*\("),
        re.compile(r"\b__construct\b"),
        re.compile(r"\b__destruct\b"),
        re.compile(r"^\s*public\s+function\s+"),
        re.compile(r"^\s*protected\s+\$"),
        re.compile(r"^\s*private\s+\$"),
        re.compile(r"array\s*\("),
    ],
    "bash": [
        re.compile(r"^#!"),
        re.compile(r"^\s*export\s+\w+="),
        re.compile(r"^\s*source\s+"),
        re.compile(r"^\s*sudo\s+"),
        re.compile(r"^\s*apt(\-get)?\s+"),
        re.compile(r"^\s*npm\s+"),
        re.compile(r"^\s*pip\d*\s+"),
        re.compile(r"^\s*git\s+"),
        re.compile(r"^\s*docker\s+"),
        re.compile(r"^\s*yarn\s+"),
        re.compile(r"^\s*npx\s+"),
        re.compile(r"^\s*node\s+"),
        re.compile(r"^\s*python\d*\s+"),
        re.compile(r"^\s*composer\s+"),
        re.compile(r"^\s*if\s+\["),
        re.compile(r"^\s*\$\(|^\s*\$\{"),
        re.compile(r"^\s*echo\s+"),
        re.compile(r"^\s*\$\s+\w+"),                 # leading "$ " shell prompt
    ],
    "sql": [
        re.compile(r"\bSELECT\b\s+.+\bFROM\b", re.IGNORECASE),
        re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
        re.compile(r"\bUPDATE\s+\w+\s+SET\b", re.IGNORECASE),
        re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
        re.compile(r"\bCREATE\s+TABLE\b", re.IGNORECASE),
        re.compile(r"\bALTER\s+TABLE\b", re.IGNORECASE),
        re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
        re.compile(r"\bJOIN\b\s+\w+", re.IGNORECASE),
        re.compile(r"\bWHERE\s+\w+\s*=", re.IGNORECASE),
    ],
    "json": [
        re.compile(r'^\s*[\{\[]\s*$'),
        re.compile(r'^\s*\}', re.MULTILINE),
        re.compile(r'^\s*\]', re.MULTILINE),
        re.compile(r'^\s*"[^"]+"\s*:', re.MULTILINE),
    ],
}


class MarkdownRenderer(IRenderer):
    """Render a PDF document as Markdown.

    Args:
        config: Optional :class:`ConversionConfig`; defaults apply otherwise.
    """

    def __init__(self, config: ConversionConfig | None = None) -> None:
        self._config = config or ConversionConfig()

    def render(self, document: PdfDocument) -> MarkdownDocument:
        """Render the given PDF document into Markdown.

        Args:
            document: The PDF document to render.

        Returns:
            A populated :class:`MarkdownDocument`.

        Raises:
            RenderingError: If the renderer cannot complete.
        """
        try:
            font_levels = HeadingInferer.infer_levels(document)
            frontmatter = (
                FrontmatterBuilder.build(
                    document.metadata, page_count=document.page_count
                )
                if self._config.frontmatter
                else ""
            )
            pages: list[MarkdownPage] = []
            for page in document.pages:
                # v0.2.0: re-join fragmented paragraph lines before
                # rendering. The PyMuPDF extractor emits one block per
                # visual line, which makes prose unreadable.
                joined_blocks = ParagraphJoiner.join(page.blocks)
                # v0.2.0: assign captions to images from nearby text
                # blocks before rendering.
                infer_captions(page.images, joined_blocks)
                page_with_joined = page
                page_with_joined.blocks = joined_blocks
                rendered = self._render_page(page_with_joined, font_levels)
                if rendered:
                    pages.append(
                        MarkdownPage(
                            page_number=page.page_number, content=rendered
                        )
                    )
            assets_dir = (
                document.file_path.parent / self._config.assets_subdir
                if document.file_path
                else None
            )
            return MarkdownDocument(
                source_pdf=document.file_path,
                pages=pages,
                assets_dir=assets_dir,
                frontmatter=frontmatter,
            )
        except RenderingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RenderingError(
                f"failed to render {document.file_path}: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Page rendering
    # ------------------------------------------------------------------

    def _render_page(
        self,
        page: PdfPage,
        font_levels: dict[str, int],
    ) -> str:
        """Render a single page to its Markdown body."""
        chunks: list[str] = []
        image_index = 0
        code_lines: list[str] = []
        list_marker: str | None = None
        for block in page.blocks:
            # Standalone bullet or numbered marker → combine with next block
            stripped = block.text.strip()
            if (
                block.block_type in (BlockType.PARAGRAPH.value, BlockType.LIST_ITEM.value)
                and (stripped == "●" or re.match(r"^\d+[.)]\s*$", stripped))
            ):
                if stripped == "●":
                    list_marker = "-"
                else:
                    list_marker = stripped
                continue

            if list_marker is not None:
                if code_lines:
                    chunks.append(self._flush_code(code_lines))
                    code_lines = []
                text = f"{list_marker} {block.text.lstrip()}"
                chunks.append(self._escape_leading_hash(text))
                list_marker = None
                continue

            if block.block_type == BlockType.HEADING.value or (
                block.block_type == BlockType.PARAGRAPH.value
                and HeadingInferer.looks_like_heading(block, font_levels)
            ):
                if code_lines:
                    chunks.append(self._flush_code(code_lines))
                    code_lines = []
                level = HeadingInferer.resolve_level(block, font_levels)
                chunks.append(self._format_heading(_escape_html_in_text(block.text), level))
            elif block.block_type == BlockType.CODE.value:
                code_lines.append(block.text)
            elif block.block_type == BlockType.LIST_ITEM.value:
                if code_lines:
                    chunks.append(self._flush_code(code_lines))
                    code_lines = []
                chunks.append(self._escape_leading_hash(_escape_html_in_text(block.text)))
            else:
                if code_lines:
                    chunks.append(self._flush_code(code_lines))
                    code_lines = []
                chunks.append(self._escape_leading_hash(_escape_html_in_text(block.text)))
        if code_lines:
            chunks.append(self._flush_code(code_lines))

        # Tables
        for table in page.tables:
            chunks.append(self._render_table(table))

        # Images
        for image in page.images:
            image_index += 1
            chunks.append(self._render_image(image, image_index))

        # Links — only when the user explicitly opts in. Default off
        # because the in-text references are usually enough and a link
        # dump at the page bottom is noisy.
        if self._config.emit_link_list and page.links:
            link_lines: list[str] = []
            for link in page.links:
                if link.is_internal:
                    continue
                text = link.text or link.url
                link_lines.append(f"- [{text}]({link.url})")
            if link_lines:
                chunks.append("\n".join(link_lines))

        return "\n\n".join(c for c in chunks if c)

    def _render_table(self, table: TableNode) -> str:
        """Render a table to GFM Markdown, a code block, or plain paragraphs.

        Tables whose cells look like code are rendered as fenced code
        blocks. Single-column tables whose cells look like natural
        language are rendered as joined paragraphs. Everything else
        becomes a standard GFM table.
        """
        cells = list(table.headers) + [
            cell for row in table.rows for cell in row
        ]

        if not table.headers and not table.rows:
            return _TABLE_FAIL_MARKER.format(
                page=table.page_number, bbox=list(table.bbox)
            )

        if _looks_like_code(cells):
            code = "\n".join(
                c for c in cells
                if c.strip() and not re.match(r"^col\d+$", c.strip())
            )
            lang = _detect_code_lang(cells)
            return f"```{lang}\n{code}\n```"

        # Determine width and headers with sane fallbacks.
        rows: list[list[str]] = [
            [_sanitize_cell(c) for c in row] for row in table.rows
        ]
        width = max(
            (len(r) for r in rows),
            default=0,
        )
        if table.headers:
            width = max(width, len(table.headers))
        if width == 0:
            return _TABLE_FAIL_MARKER.format(
                page=table.page_number, bbox=list(table.bbox)
            )

        # Single-column prose -> joined paragraphs
        if width <= 1 and _looks_like_prose(cells):
            return "\n\n".join(
                c.strip()
                for c in cells
                if c.strip() and not re.match(r"^col\d+$", c.strip())
            )

        if table.headers:
            headers = [_sanitize_cell(h) for h in table.headers]
            body = rows
        else:
            headers = [f"col{i + 1}" for i in range(width)]
            body = rows

        def _line(cells: Iterable[str]) -> str:
            cells = list(cells) + [""] * (width - len(list(cells)))
            return "| " + " | ".join(cells[:width]) + " |"

        header_line = _line(headers)
        separator = "| " + " | ".join("---" for _ in range(width)) + " |"
        body_lines = [_line(r) for r in body]
        return "\n".join([header_line, separator, *body_lines])

    @staticmethod
    def _escape_leading_hash(text: str) -> str:
        if text.startswith("#"):
            return "\\" + text
        return text

    def _render_image(self, image: ImageAsset, index: int) -> str:
        """Render an image asset as a Markdown reference."""
        ext = (image.format or "png").lower().replace("jpeg", "jpg")
        slug = (
            image.output_path.name
            if image.output_path
            else f"{image.image_id}.{ext}"
        )
        caption = image.caption or f"Figure {index}"
        return f"![{caption}]({self._config.assets_subdir}/{slug})"

    def _flush_code(self, lines: list[str]) -> str:
        return _render_code_block(lines, fence=self._config.code_fence)

    def _format_heading(self, text: str, level: int) -> str:
        """Format a heading per the configured style.

        Levels above 6 are clamped to 6. Setext only renders for
        levels 1 and 2; anything else is emitted in ATX.
        """
        level = max(1, min(6, level))
        text = text.strip()
        if self._config.heading_style == HeadingStyle.SETEXT and level <= 2:
            underline = "=" if level == 1 else "-"
            return f"{text}\n{underline * max(3, len(text))}"
        return f"{'#' * level} {text}"


_PIPE_RE = re.compile(r"[|]")
_NEWLINE_RE = re.compile(r"[\r\n]+")

# Pattern to match HTML/JSX tags in text (opening, closing, self-closing)
_HTML_TAG_IN_TEXT_RE = re.compile(r"<(/?)(\w[\w-]*)([^>]*?)(/?)\s*>")

def _escape_html_in_text(text: str) -> str:
    """Escape HTML tags in prose text by prefixing '<' with '+'.

    Converts ``<script setup>`` → ``<+script setup>`` so Markdown renderers
    display the tag literally instead of interpreting it as HTML.  Only
    applies to non-code text blocks; code blocks are handled separately by
    _render_code_block.

    Args:
        text: The text to process.

    Returns:
        Text with HTML tags escaped for literal display in Markdown.
    """
    def _replace_tag(m: re.Match) -> str:
        return f"<+{m.group(1)}{m.group(2)}{m.group(3)}{m.group(4)}>"
    return _HTML_TAG_IN_TEXT_RE.sub(_replace_tag, text)


def _looks_like_code(cells: list[str]) -> bool:
    code_hits = 0
    total = 0
    for cell in cells:
        text = cell.strip()
        if not text:
            continue
        total += 1
        if any(p.search(text) for p in _CODE_PATTERNS):
            code_hits += 1
    if total == 0:
        return False
    return code_hits / total > 0.2


def _looks_like_prose(cells: list[str]) -> bool:
    joined = " ".join(cells)
    has_spanish = any(c in joined.lower() for c in ["á", "é", "í", "ó", "ú", "ñ"])
    avg_len = sum(len(c) for c in cells) / max(len(cells), 1)
    return avg_len > 40 or has_spanish


def _detect_code_lang(cells: list[str]) -> str:
    """Detect code language from content.

    Scores each language's patterns against the cell content and returns
    the best match above threshold.  Falls back to ``"ts"`` (TypeScript).
    """
    total = sum(1 for c in cells if c.strip())
    if total == 0:
        return ""

    scores: dict[str, float] = {}
    for lang, patterns in _LANG_PATTERNS.items():
        hits = sum(
            1 for c in cells
            if c.strip() and any(p.search(c) for p in patterns)
        )
        scores[lang] = hits / total

    # Priority order: more specific languages first.
    # vue is more specific than html; html is more specific than css;
    # css/python/php/bash/sql/json follow; ts is the fallback.
    for lang in ("vue", "html", "css", "python", "php", "bash", "sql", "json"):
        if scores.get(lang, 0) > 0.25:
            return lang
    return "ts"


def _sanitize_cell(text: str) -> str:
    """Sanitize a cell for GFM tables."""
    if text is None:
        return ""
    text = _NEWLINE_RE.sub(" ", str(text))
    text = _PIPE_RE.sub("\\|", text)
    return text.strip()


# ----------------------------------------------------------------------
# Code block rendering (v0.3.0: SFC-aware)
# ----------------------------------------------------------------------

# A line is part of a Vue Single-File Component if it opens, closes or
# is enclosed by one of these tags.
_SFC_TAG_RE = re.compile(
    r"^\s*</?(?:template|script(?:\s+setup)?|style(?:\s+scoped)?)(?:\s[^>]*)?>\s*$",
    re.IGNORECASE,
)
_SFC_HAS_DIRECTIVE_RE = re.compile(
    r"\b(?:v-bind|v-if|v-for|v-model|v-on|v-show)\b"
)


def _is_sfc_block(lines: list[str]) -> bool:
    """Return True if ``lines`` form a Vue SFC.

    An SFC is recognised by the presence of ``<template>``/``</template>``,
    ``<script setup>``/``</script>`` or ``<style>``/``</style>`` pairs, or
    by the presence of any Vue directive (``v-bind``, ``v-if``, ...).
    """
    has_open = any(
        re.match(r"^\s*<(template|script|style)\b", ln, re.IGNORECASE)
        for ln in lines
    )
    has_close = any(
        re.match(r"^\s*</(template|script|style)\s*>\s*$", ln, re.IGNORECASE)
        for ln in lines
    )
    has_directive = any(_SFC_HAS_DIRECTIVE_RE.search(ln) for ln in lines)
    # A block is an SFC when it has at least one opening AND one closing
    # tag, OR any Vue directive. A single ``<script>`` opener is not
    # enough on its own — that could be plain HTML.
    return (has_open and has_close) or has_directive


def _render_code_block(
    lines: list[str],
    *,
    fence: str = "```",
) -> str:
    """Render a code block as a single fenced Markdown chunk.

    v0.3.0: detects Vue SFC and emits a single ````vue`` fence around
    the whole block, instead of opening/closing a fence per language
    shift inside the block (the v0.2.0 bug that produced
    ````vue\n<script setup>\n```\nconst items = ...\n```ts\n</script>\n```\n``).
    """
    if _is_sfc_block(lines):
        lang = "vue"
    else:
        lang = _detect_code_lang(lines)
    return f"{fence}{lang}\n" + "\n".join(lines) + f"\n{fence}"


__all__ = ["MarkdownRenderer", "_render_code_block"]

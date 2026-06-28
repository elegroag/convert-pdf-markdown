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
from pdf2md.domain.services.code_line_joiner import CodeLineJoiner
from pdf2md.domain.services.block_sanitizer import BlockSanitizer
from pdf2md.domain.services.frontmatter_builder import FrontmatterBuilder
from pdf2md.domain.services.heading_inferer import HeadingInferer
from pdf2md.domain.services.page_noise_filter import PageNoiseFilter
from pdf2md.domain.services.paragraph_joiner import ParagraphJoiner
from pdf2md.domain.services.section_number_joiner import SectionNumberJoiner
from pdf2md.domain.value_objects.enums import BlockType, HeadingStyle
from pdf2md.domain.value_objects.value_objects import ContentBlock, ConversionConfig

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
    "ts": [
        re.compile(r"^\s*import\s+type\b"),
        re.compile(r":\s*(?:string|number|boolean|any|unknown|never|void)\b"),
        re.compile(r"\binterface\s+\w+\s*\{"),
        re.compile(r"\btype\s+\w+\s*="),
        re.compile(r"\benum\s+\w+\s*\{"),
        re.compile(r"<\w+>\("),                       # generic function call
        re.compile(r"\bas\s+(?:const|const\s+\w+|any|unknown|never)\b"),
        re.compile(r"\breadonly\s+\w+"),
        re.compile(r"\?\s*:"),                        # optional / ternary type
        re.compile(r"\|\s*undefined\b"),
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
            all_blocks = [b for page in document.pages for b in page.blocks]
            body_size = HeadingInferer._compute_body_size(all_blocks)
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
                blocks = PageNoiseFilter.filter(page.blocks)
                blocks = BlockSanitizer.demote_false_headings(blocks)
                blocks = SectionNumberJoiner.join(blocks)
                joined_blocks = ParagraphJoiner.join(blocks)
                # v0.2.0: assign captions to images from nearby text
                # blocks before rendering.
                infer_captions(page.images, joined_blocks)
                page_with_joined = page
                page_with_joined.blocks = joined_blocks
                rendered = self._render_page(
                    page_with_joined, font_levels, body_size=body_size
                )
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
        *,
        body_size: float = 0.0,
    ) -> str:
        """Render a single page to its Markdown body."""
        chunks: list[str] = []
        image_index = 0
        # Accumulate code blocks as ContentBlock so we can apply CodeLineJoiner
        # (re-joins mid-statement lines that PyMuPDF extracted separately).
        code_buffer: list[ContentBlock] = []
        list_marker: str | None = None
        for block in page.blocks:
            # Standalone bullet or numbered marker → combine with next block
            stripped = block.text.strip()
            # A paragraph that BEGINS with ``●​`` (bullet + zero-width
            # space + text) is already a list item, no splitting needed.
            # The zero-width space comes from PyMuPDF when the bullet
            # glyph is glued to the next visual line.
            if (
                block.block_type == BlockType.PARAGRAPH.value
                and re.match(r"^●\u200b?\s+\S", stripped)
            ):
                if code_buffer:
                    chunks.append(self._flush_code(code_buffer))
                    code_buffer = []
                chunks.append(
                    self._escape_leading_hash("- " + re.sub(r"^●\u200b?\s+", "", stripped))
                )
                continue
            if (
                block.block_type in (BlockType.PARAGRAPH.value, BlockType.LIST_ITEM.value)
                and (
                    re.match(r"^●(\u200b)?\s*$", stripped)
                    or re.match(r"^\d+[.)]\s*$", stripped)
                )
            ):
                if re.match(r"^●", stripped):
                    list_marker = "-"
                else:
                    list_marker = stripped
                continue

            if list_marker is not None:
                if code_buffer:
                    chunks.append(self._flush_code(code_buffer))
                    code_buffer = []
                text = f"{list_marker} {block.text.lstrip()}"
                chunks.append(self._escape_leading_hash(text))
                list_marker = None
                continue

            is_heading = block.block_type == BlockType.HEADING.value or (
                block.block_type == BlockType.PARAGRAPH.value
                and HeadingInferer.looks_like_heading(
                    block, font_levels, body_size=body_size
                )
            )
            if is_heading:
                if code_buffer:
                    chunks.append(self._flush_code(code_buffer))
                    code_buffer = []
                level = HeadingInferer.resolve_level(block, font_levels)
                if level <= 0:
                    level = 1
                chunks.append(self._format_heading(block.text.strip(), level))
            elif block.block_type == BlockType.CODE.value:
                code_buffer.append(block)
            elif block.block_type == BlockType.LIST_ITEM.value:
                if code_buffer:
                    chunks.append(self._flush_code(code_buffer))
                    code_buffer = []
                chunks.append(self._escape_leading_hash(_escape_html_in_text(block.text)))
            else:
                # PARAGRAPH block — check if it's actually HTML/code misclassified
                if _is_pure_html_block(block.text) or _looks_like_code_line(block.text):
                    # Treat as code block to preserve formatting
                    code_buffer.append(block)
                elif _is_html_fragment_paragraph(block.text):
                    # Lines that OPEN with a tag (e.g. ``<template> <div>...``)
                    # are always code fragments — never prose. Treating them
                    # as prose would either escape their tags (corrupting
                    # the surrounding code) or render them as raw HTML
                    # that the Markdown reader would interpret. Accumulate
                    # them into the code buffer instead.
                    code_buffer.append(block)
                elif _is_sfc_continuation(code_buffer, block.text):
                    # The current SFC / code block did NOT close on the
                    # last accumulated block (e.g. a ``<script>`` block
                    # with no ``</script>``) and this paragraph looks
                    # like its body. Keep accumulating so the result is
                    # a single fenced chunk instead of an SFC + loose
                    # paragraph + new fence.
                    code_buffer.append(block)
                else:
                    # Flush any pending code before emitting prose
                    if code_buffer:
                        chunks.append(self._flush_code(code_buffer))
                        code_buffer = []
                    chunks.append(self._escape_leading_hash(_escape_html_in_text(block.text)))
        if code_buffer:
            chunks.append(self._flush_code(code_buffer))

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

        return self._dedupe_consecutive_chunks(
            "\n\n".join(c for c in chunks if c)
        )

    @staticmethod
    def _dedupe_consecutive_chunks(text: str) -> str:
        """Drop chunks that are near-duplicates of the previous chunk.

        PyMuPDF sometimes emits the same paragraph twice (e.g. once as
        the figure caption and once as the figure body). When the
        rendered chunks are >85% identical, we drop the second one to
        keep the output readable.
        """
        if not text:
            return text
        chunks = text.split("\n\n")
        kept: list[str] = []
        for chunk in chunks:
            if kept and MarkdownRenderer._is_duplicate(kept[-1], chunk):
                continue
            kept.append(chunk)
        return "\n\n".join(kept)

    @staticmethod
    def _is_duplicate(prev: str, nxt: str) -> bool:
        """Return True if ``nxt`` is a near-duplicate of ``prev``."""
        if not prev or not nxt:
            return False
        # Strip whitespace + non-word noise for comparison.
        norm_prev = re.sub(r"\s+", " ", prev).strip().lower()
        norm_nxt = re.sub(r"\s+", " ", nxt).strip().lower()
        if not norm_prev or not norm_nxt:
            return False
        # Exact match.
        if norm_prev == norm_nxt:
            return True
        # Length-based similarity (Dice / overlap).
        shorter, longer = (
            (norm_prev, norm_nxt) if len(norm_prev) <= len(norm_nxt) else (norm_nxt, norm_prev)
        )
        if len(shorter) < 20:
            return False
        return shorter in longer and len(shorter) / len(longer) >= 0.85

    def _render_table(self, table: TableNode) -> str:
        """Render a table to GFM Markdown, a code block, or plain paragraphs.

        Tables whose cells look like code are rendered as fenced code
        blocks. Single-column tables whose cells look like natural
        language are rendered as joined paragraphs. Everything else
        becomes a standard GFM table.

        v2.0.0: returns an empty string for tables with no usable content
        (empty headers AND empty rows). Cover pages often produce
        placeholder tables with no cells; emitting them as GFM stubs
        ("| col1 | / | --- | / | |") pollutes the output.
        """
        cells = list(table.headers) + [
            cell for row in table.rows for cell in row
        ]
        non_empty = [c for c in cells if c and c.strip()]

        # Discard cover-page placeholders and other empty tables.
        if not non_empty:
            return ""

        # Cover-page sections often arrive as a 1-column table whose
        # rows hold section titles like "VUE JS 3", "Convenciones
        # utilizadas", "Para quién es este libro". Emitting them as a
        # GFM table is misleading. When the table has 1 column and
        # each non-empty cell is a short section title, we drop the
        # table entirely — the section titles are usually rendered
        # elsewhere as headings.
        if (
            self._looks_like_cover_section_table(table)
        ):
            return ""

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
            return ""

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

    @staticmethod
    def _looks_like_cover_section_table(table: TableNode) -> bool:
        """Heuristic: a 1-column table where every cell is a section title.

        Cover pages from Google Docs frequently emit a layout table
        whose rows are section headings (e.g. "VUE JS 3", "Para quién
        es este libro", "Convenciones utilizadas"). Rendering them as
        GFM tables clutters the output. We detect them by:

        1. 1 column wide,
        2. at least 2 non-empty cells (single-cell tables are
           preserved),
        3. every non-empty cell is short (<40 chars),
        4. the cell text does not look like a complete prose sentence
           (no terminal punctuation), AND
        5. the table is "noisy" — at least 30% of cells are empty.
           That distinguishes cover layout tables (where empty cells
           are spacers) from real data tables.
        """
        if table.headers and len(table.headers) != 1:
            return False
        # Count columns in rows
        widths = [len(r) for r in table.rows if r]
        if not widths or any(w != 1 for w in widths):
            return False
        # Collect every cell (including empty ones) to compute noise.
        all_cells: list[str] = []
        if table.headers:
            all_cells.extend(table.headers)
        for row in table.rows:
            all_cells.extend(row)
        if not all_cells:
            return False
        empty = sum(1 for c in all_cells if not (c and c.strip()))
        # Cover-page tables are mostly empty spacers with one or two
        # title cells. A real data table has very few empty cells.
        if empty / len(all_cells) < 0.50:
            return False
        # Check that cells are short section titles, not paragraphs.
        non_empty = [c.strip() for c in all_cells if c and c.strip()]
        if len(non_empty) < 1:
            return False
        # Every non-empty cell must be short, not end in punctuation,
        # and look like a TITLE rather than a single token. A single
        # lowercase word like ``"text"`` could be a real data cell, so
        # we require either multiple words or mostly uppercase.
        # Placeholder cells (the ``col1`` / ``col2`` defaults that
        # pdfplumber emits when no header was found) are also OK.
        for c in non_empty:
            if re.match(r"^col\d+$", c):
                continue
            if len(c) > 40:
                return False
            # A prose sentence ends in .!?:; — section titles don't.
            if c[-1] in ".!?:;":
                return False
            words = c.split()
            if len(words) >= 2:
                continue
            # Single word: require uppercase or capitalized.
            if c.isupper() or c != c.lower():
                continue
            return False
        return True

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

    def _flush_code(self, blocks: list[ContentBlock]) -> str:
        """Render accumulated code blocks as a single fenced chunk.

        Applies :class:`CodeLineJoiner` first to re-join mid-statement
        lines that PyMuPDF split across multiple visual lines.
        """
        if not blocks:
            return ""
        joined = CodeLineJoiner.join(blocks)
        lines = [b.text for b in joined]
        # Escape any line that opens with triple backticks so the outer
        # fence is not closed prematurely by an internal one.
        sanitized = [_sanitize_fence_line(ln) for ln in lines]
        return _render_code_block(sanitized, fence=self._config.code_fence)

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
# Internal fences inside a code block need to be padded with a space so
# they do NOT close the outer fence.
_FENCE_LINE_RE = re.compile(r"^(\s*)(`{3,})")


def _sanitize_fence_line(line: str) -> str:
    """Pad leading triple backticks so they do not close the outer fence."""
    m = _FENCE_LINE_RE.match(line)
    if not m:
        return line
    indent, ticks = m.group(1), m.group(2)
    return f"{indent} {ticks}"

# Pattern to match HTML/JSX tags in text (opening, closing, self-closing)
_HTML_TAG_IN_TEXT_RE = re.compile(r"<(/?)(\w[\w-]*)([^>]*?)(/?)\s*>")

# Pattern to detect if a line is an HTML tag (opening, closing, or self-closing)
# This regex is more permissive to allow > inside attribute values
_HTML_LINE_RE = re.compile(r"^\s*<[^!][^>]*>\s*$")
# More permissive version that allows > inside attribute values
_HTML_LINE_PERMISSIVE_RE = re.compile(r"^\s*<[^!][\s\S]*?>\s*$")

# Pattern to detect if a line is a DOCTYPE or similar HTML declaration
_HTML_DECL_RE = re.compile(r"^\s*<!DOCTYPE[^>]*>\s*$", re.IGNORECASE)

# Pattern to detect if a line looks like code (for classification purposes)
_CODE_LINE_RE = re.compile(
    r"(^\s*(export|import|const|let|var|function|class|return|def|if|for|while|async)\s+)"
    r"|(^\s*//)|(^\s*/\*)|(=>)|(\$\{)"
    r"|(^\s*\{.*\}\s*$)"  # Single line with braces
    r"|(^\s*\}[\s,;\)]*\s*$)"  # Closing brace
)


def _is_pure_html_block(text: str) -> bool:
    """Return True if the text consists only of HTML tags.

    Detects blocks like ``<!DOCTYPE html>\\n<html>\\n<head>`` that were
    mis-classified as paragraphs by PyMuPDF but are actually code.
    """
    lines = text.splitlines()
    if len(lines) < 1:
        return False
    html_lines = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _HTML_LINE_PERMISSIVE_RE.match(stripped) or _HTML_DECL_RE.match(stripped):
            html_lines += 1
    # If ALL non-empty lines are HTML tags, treat as code
    return html_lines > 0 and html_lines == len([l for l in lines if l.strip()])


_HTML_FRAGMENT_START_RE = re.compile(
    r"^\s*<(/)?[a-zA-Z][\w-]*(\s|/?>|$)"
)


def _is_html_fragment_paragraph(text: str) -> bool:
    """Return True when the paragraph opens with an HTML tag fragment.

    Lines like ``<template> <div>...</div>`` are mid-SFC fragments that
    PyMuPDF classified as paragraphs. Treating them as prose corrupts
    the output (their tags get escaped, then the reader sees
    ``&lt;template&gt;`` mid-paragraph). Routing them through the code
    buffer keeps them inside a fenced code block.

    Pure-prose paragraphs (e.g. "Para conocer la arquitectura de Vue,
    comenzaremos importando el paquete Vue a través de la Red de
    distribución de contenido (CDN) oficial") never start with ``<``,
    so the check is safe.
    """
    if not text:
        return False
    first_line = text.splitlines()[0]
    if not _HTML_FRAGMENT_START_RE.match(first_line):
        return False
    # A line that opens with an HTML tag is almost always a code
    # fragment. We do not need to also require the rest of the line to
    # be HTML — multi-line SFC bodies often have prose between tags.
    return True


_SFC_CLOSING_TAGS_RE = re.compile(
    r"</(template|script|style)\s*>",
    re.IGNORECASE,
)
_JS_LIKE_CONTINUATION_RE = re.compile(
    r"(^\s*"
    r"(export|import|const|let|var|function|class|return|if|else|for|while|"
    r"async|await|this|new)\b"
    r")"
    r"|(^\s*[\}\)\],;\s]+\s*$)"  # closing brackets, terminators, or whitespace
    r"|(^\s*\.\w+\s*\()",        # chained method call
    re.MULTILINE,
)


def _is_sfc_continuation(
    code_buffer: list[ContentBlock],
    candidate: str,
) -> bool:
    """Return True if ``candidate`` is the continuation of an open SFC.

    The accumulator's last text fragment is the trigger: if it ends
    mid-SFC (e.g. an unclosed ``<script>`` block, an unfinished object
    literal), then a paragraph that looks like JavaScript (export,
    return, closing braces, etc.) must be appended to the same code
    block instead of rendered as a separate paragraph.
    """
    if not code_buffer:
        return False
    last_text = code_buffer[-1].text
    # An SFC body is open if the last text opens a top-level SFC tag
    # whose closing partner is missing.
    has_open_sfc_tag = bool(
        re.search(r"<(template|script|style)\b[^>]*>", last_text, re.IGNORECASE)
        and not _SFC_CLOSING_TAGS_RE.search(last_text)
    )
    # An object literal or function body is open if the last text has
    # un-balanced braces / brackets.
    depth = (
        last_text.count("{") - last_text.count("}")
        + last_text.count("(") - last_text.count(")")
        + last_text.count("[") - last_text.count("]")
    )
    has_open_body = depth > 0
    if not (has_open_sfc_tag or has_open_body):
        return False
    # Only treat as continuation if the candidate itself looks like
    # code (otherwise we'd happily absorb a Spanish sentence).
    if not _JS_LIKE_CONTINUATION_RE.search(candidate):
        return False
    return True


def _looks_like_code_line(text: str) -> bool:
    """Return True if the text looks like a line of code.

    v2.0.0: less aggressive than the v1 implementation. A line of natural
    prose that happens to mention ``(paréntesis)`` is no longer captured as
    code. We require an explicit code marker: either a keyword like
    ``const``/``function``, or a balanced pair of braces, or a method call
    that ends with a statement terminator (``;`` or ``)``).
    """
    stripped = text.strip()
    if not stripped:
        return False
    # 1) Reject long lines that look like prose with embedded parentheses.
    #    Spanish prose averages ~60 chars per sentence; longer lines that
    #    end in punctuation almost never need to be in a code block.
    if len(stripped) > 80 and stripped.endswith(tuple(".,;:!?")):
        return False
    # 2) Lines ending in closing paren + sentence punctuation like "()." are
    #    almost certainly prose mentions, not code statements.
    if re.search(r"[.!?]\s*$", stripped) and not _CODE_LINE_RE.search(stripped):
        return False
    # 3) Explicit code patterns (const/function/return/etc.) — high signal.
    if _CODE_LINE_RE.search(stripped):
        return True
    # 4) Balanced braces in a single line are usually a JS object literal.
    if "{" in stripped and "}" in stripped:
        # Vue template interpolation ``{{ expr }}`` in prose should NOT
        # be treated as code (e.g. ``dentro de las llaves dobles {{}}``).
        if "{{" in stripped and "}}" in stripped and "{" not in stripped.replace("{{", ""):
            # Only contains double-brace interpolation, no other braces.
            pass
        # But exclude lines that look like prose with `{word}` citations.
        elif not re.search(r"[a-záéíóúñ]\s*\{[^}]+\}\s*[a-záéíóúñ]", stripped, re.IGNORECASE):
            return True
    # 5) Method call statements: foo() or obj.bar() that end with a
    #    statement terminator. Avoid the ".mount('#x')" inside prose by
    #    requiring the line to be short.
    if (
        "." in stripped
        and "(" in stripped
        and ")" in stripped
        and len(stripped) < 80
        and stripped.endswith((")", ";", "=>", ","))
    ):
        return True
    # 6) Pure HTML tags (handled by _is_pure_html_block; here we just
    #    detect single-line HTML like <div>...</div>).
    if _HTML_LINE_PERMISSIVE_RE.match(stripped) or _HTML_DECL_RE.match(stripped):
        return True
    # 7) Shell commands: ``node -v``, ``npm install``, ``yarn dev``,
    #    ``cd path/to/dir``, ``$ command`` (prompt). Keep the check
    #    conservative — only short lines that start with a known
    #    shell verb.
    if _looks_like_shell_command(stripped):
        return True
    return False


_SHELL_VERB_RE = re.compile(
    r"^\s*"
    r"(\$|>|\.{1,2}/)"
    r"|"
    r"^\s*(?:"
    r"cd|ls|cat|mkdir|rm|cp|mv|touch|chmod|chown|"
    r"npm|pnpm|yarn|npx|nvm|node|deno|bun|"
    r"git|gh|docker|docker-compose|"
    r"python|pip|pip3|python3|"
    r"sudo|apt|apt-get|brew|"
    r"code|vim|nano|less|more|"
    r"export|source|echo|"
    r"curl|wget|http|"
    r"tar|zip|unzip|"
    r"ps|kill|killall|grep|find|"
    r"ssh|scp|rsync"
    r")\b"
)


def _looks_like_shell_command(text: str) -> bool:
    """Return True if ``text`` looks like a single shell command line.

    Used to convert lines that PyMuPDF extracted as paragraphs but
    that are clearly terminal commands (e.g. ``node -v``,
    ``$ yarn dev``) into code lines so they render as code blocks
    instead of plain prose.
    """
    stripped = text.strip()
    if not stripped:
        return False
    if len(stripped) > 120:
        return False
    if not _SHELL_VERB_RE.match(stripped):
        return False
    # A shell command rarely ends with Spanish punctuation.
    if stripped.endswith(tuple("áéíóúñ.,;:?")):
        return False
    return True


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _prose_html_ratio(text: str) -> float:
    """Return the share of characters that belong to HTML tags.

    A line like ``<div>foo</div>`` scores 1.0. A line like
    ``usando el tag <div> dentro del HTML`` scores around 0.1. We use
    the ratio to decide whether escaping is needed at all.
    """
    stripped = text.strip()
    if not stripped:
        return 0.0
    total = len(stripped)
    html_chars = sum(len(m.group(0)) for m in _HTML_TAG_RE.finditer(stripped))
    return html_chars / total


def _escape_html_in_text(text: str) -> str:
    """Escape HTML tags in prose text using HTML entities.

    v2.0.0: contextual escape. The function is no longer applied
    indiscriminately to every paragraph — that produced illegible output
    like::

        Los tres componentes principales que componen un componente de
        un solo archivo son los bloques <template>, <script> y <style>.

    When the text is mostly prose with a tiny tag citation, the tag is
    kept as-is. Only when the text is dominated by HTML (high
    :func:`_prose_html_ratio` or starts with ``<!DOCTYPE`` / a closing
    tag) do we apply the entity escape.
    """
    stripped = text.strip()
    if not stripped:
        return text
    # Lines that look like code blocks should be escaped aggressively.
    if _is_pure_html_block(text):
        return text.replace("<", "&lt;").replace(">", "&gt;")
    # If the line is dominated by HTML tags, escape them so they render
    # as literal text in Markdown.
    if _prose_html_ratio(text) >= 0.35:
        return text.replace("<", "&lt;").replace(">", "&gt;")
    # Lines that open with a closing tag (e.g. </body>, </script>) are
    # almost always a code fragment that lost its opener on a previous
    # page — escape them so they do not render as broken HTML.
    if re.match(r"^\s*</[a-zA-Z][\w-]*", text):
        return text.replace("<", "&lt;").replace(">", "&gt;")
    # Default: leave prose intact. Short tag mentions like
    # ``<script setup>`` read better in raw form.
    return text


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
    the best match above threshold. Vue is checked first because Vue SFCs
    contain plain JS/TS fragments that would otherwise score high on
    "ts". Falls back to ``"ts"`` (TypeScript) for plain JS/TS snippets.
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
    # css/python/php/bash/sql/json/ts follow.
    for lang in ("vue", "html", "css", "python", "php", "bash", "sql", "json", "ts"):
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

    An SFC is recognised by:

    - the presence of ``<template>``/``</template>``,
      ``<script setup>``/``</script>`` or ``<style>``/``</style>`` pairs, OR
    - the presence of any Vue directive (``v-bind``, ``v-if``, ...), OR
    - the presence of a Vue SFC opener (``<template>``, ``<script>``,
      ``<script setup>``, ``<style>``) — even if the closing tag is in
      a different chunk (e.g. a snippet that spans multiple pages).
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
    has_setup = any(
        re.match(r"^\s*<script\s+setup\b", ln, re.IGNORECASE) for ln in lines
    )
    # Full pair or any directive → unambiguously SFC.
    if (has_open and has_close) or has_directive:
        return True
    # A lone opener with ``setup`` (most common in v2.x books) is also
    # SFC — the closing tag may live on the next page.
    if has_setup:
        return True
    return False


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

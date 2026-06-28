"""Markdown renderer for spreadsheet sheets."""

from __future__ import annotations

from tabulate import tabulate

from xlsx2md.domain.entities.entities import (
    EmptySheet,
    HeadingBlock,
    ImageBlock,
    ImageSheet,
    KeyValueBlock,
    MarkdownDocument,
    NarrativeSheet,
    ParagraphBlock,
    TableBlock,
    TableSheet,
    XlsxDocument,
)
from xlsx2md.domain.exceptions import RenderingError
from xlsx2md.domain.ports.ports import IMarkdownRenderer
from xlsx2md.domain.services.frontmatter_builder import FrontmatterBuilder
from xlsx2md.domain.value_objects.value_objects import ConversionConfig


class MarkdownRenderer(IMarkdownRenderer):
    """Convert a worksheet into Markdown."""

    def __init__(self, config: ConversionConfig | None = None) -> None:
        self._config = config or ConversionConfig()

    def render(self, document: XlsxDocument, sheet: object) -> MarkdownDocument:
        """Render a single sheet into Markdown."""
        try:
            content = self._render_sheet(sheet)
            frontmatter = self._build_frontmatter(document, sheet)

            return MarkdownDocument(
                source_xlsx=document.file_path,
                sheet_name=getattr(sheet, "name", "_index"),
                content=content,
                frontmatter=frontmatter,
            )
        except RenderingError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RenderingError(
                f"failed to render sheet {getattr(sheet, 'name', '?')}: {exc}"
            ) from exc

    def _render_sheet(self, sheet: object) -> str:
        if isinstance(sheet, NarrativeSheet):
            return self._render_narrative(sheet)
        if isinstance(sheet, TableSheet):
            return self._render_table_sheet(sheet)
        if isinstance(sheet, ImageSheet):
            return self._render_image_sheet(sheet)
        if isinstance(sheet, EmptySheet):
            return f"_{sheet.name or 'Hoja'} no contiene contenido._"
        return ""

    def _render_narrative(self, sheet: NarrativeSheet) -> str:
        chunks: list[str] = [f"# {sheet.name}"]
        for block in sheet.blocks:
            rendered = self._render_block(block)
            if rendered:
                chunks.append(rendered)

        if sheet.images:
            chunks.append(self._render_images(sheet.images))

        return "\n\n".join(chunks).strip() + "\n" if chunks else ""

    def _render_table_sheet(self, sheet: TableSheet) -> str:
        chunks: list[str] = [f"# {sheet.name}"]
        for idx, table in enumerate(sheet.tables, start=1):
            rendered = self._render_table_block(table)
            if rendered:
                if len(sheet.tables) > 1:
                    chunks.append(f"## Tabla {idx}")
                chunks.append(rendered)
        if sheet.images:
            chunks.append(self._render_images(sheet.images))
        return "\n\n".join(chunks).strip() + "\n" if chunks else ""

    def _render_image_sheet(self, sheet: ImageSheet) -> str:
        chunks: list[str] = [f"# {sheet.name}"]
        if sheet.caption:
            chunks.append(f"_{sheet.caption}_")
        chunks.append(self._render_images(sheet.images))
        return "\n\n".join(chunks).strip() + "\n"

    def _render_block(self, block: object) -> str:
        if isinstance(block, HeadingBlock):
            return f"## {block.text}"
        if isinstance(block, ParagraphBlock):
            return block.text
        if isinstance(block, KeyValueBlock):
            label = block.label.rstrip(":").strip() or "Dato"
            return f"**{label}:** {block.value}"
        if isinstance(block, TableBlock):
            return self._render_table_block(block)
        return ""

    def _render_table_block(self, block: TableBlock) -> str:
        if block.is_empty():
            return ""

        if block.headers:
            body = block.rows
            table_md = tabulate(
                body,
                headers=block.headers,
                tablefmt=self._config.table_format,
                numalign="left",
                stralign="left",
                maxcolwidths=60,
            )
        else:
            table_md = tabulate(
                block.rows,
                tablefmt=self._config.table_format,
                numalign="left",
                stralign="left",
                maxcolwidths=60,
            )
        chunks = [table_md]

        truncated = self._is_truncated(block)
        if truncated:
            chunks.append(self._truncation_note())

        if block.anchor_start and block.anchor_end:
            chunks.append(f"<!-- rango original: {block.anchor_start}:{block.anchor_end} -->")

        return "\n\n".join(chunks)

    def _is_truncated(self, block: TableBlock) -> bool:
        if self._config.max_rows is not None and len(block.rows) >= self._config.max_rows:
            return True
        if self._config.max_cols is not None:
            return True
        return False

    def _truncation_note(self) -> str:
        parts: list[str] = []
        if self._config.max_rows is not None:
            parts.append(f"{self._config.max_rows} filas")
        if self._config.max_cols is not None:
            parts.append(f"{self._config.max_cols} columnas")
        return f"*[tabla truncada a {', '.join(parts) or 'límite configurado'}]*"

    def _render_images(self, images: list[ImageBlock]) -> str:
        lines: list[str] = ["## Imágenes", ""]
        for image in images:
            alt = image.alt_text or "image"
            anchor = f" <!-- anchor: {image.anchor_cell} -->" if image.anchor_cell else ""
            lines.append(f"![{alt}]({image.filename}){anchor}")
        return "\n".join(lines)

    def _build_frontmatter(self, document: XlsxDocument, sheet: object) -> str:
        if not self._config.frontmatter:
            return ""
        return FrontmatterBuilder.build(
            document.metadata,
            sheet_name=getattr(sheet, "name", ""),
            sheet_index=getattr(sheet, "index", None),
        )


__all__ = ["MarkdownRenderer"]

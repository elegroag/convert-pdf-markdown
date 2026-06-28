"""Index renderer for workbook table of contents."""

from __future__ import annotations

from pathlib import Path

from xlsx2md.domain.entities.entities import (
    EmptySheet,
    ImageSheet,
    MarkdownDocument,
    NarrativeSheet,
    TableSheet,
    XlsxDocument,
)
from xlsx2md.domain.exceptions import RenderingError
from xlsx2md.domain.ports.ports import IIndexRenderer
from xlsx2md.domain.services.frontmatter_builder import FrontmatterBuilder
from xlsx2md.domain.value_objects.value_objects import ConversionConfig


class IndexRenderer(IIndexRenderer):
    """Render the workbook index Markdown document."""

    def __init__(self, config: ConversionConfig | None = None) -> None:
        self._config = config or ConversionConfig()

    def render(
        self,
        document: XlsxDocument,
        sheet_files: dict[str, Path],
    ) -> MarkdownDocument:
        """Build the ``_index.md`` document."""
        try:
            title = document.metadata.title or document.file_path.stem
            lines: list[str] = [f"# {title}", "", "## Hojas", ""]

            for sheet in document.sheets:
                if isinstance(sheet, EmptySheet):
                    continue
                if sheet.name not in sheet_files:
                    continue
                rel_name = sheet_files[sheet.name].name
                summary = self._summarize(sheet)
                lines.append(f"- [{sheet.name}]({rel_name}) — {summary}")

            frontmatter = ""
            if self._config.frontmatter:
                frontmatter = FrontmatterBuilder.build(document.metadata)

            return MarkdownDocument(
                source_xlsx=document.file_path,
                sheet_name="_index",
                content="\n".join(lines).strip() + "\n",
                frontmatter=frontmatter,
            )
        except Exception as exc:  # noqa: BLE001
            raise RenderingError(f"failed to render index: {exc}") from exc

    @staticmethod
    def _summarize(sheet: object) -> str:
        if isinstance(sheet, TableSheet):
            table_count = len(sheet.tables)
            row_count = sum(t.rows.__len__() for t in sheet.tables)
            image_count = len(sheet.images)
            parts = [f"{row_count} filas"]
            if table_count > 1:
                parts.insert(0, f"{table_count} tablas")
            if image_count:
                parts.append(f"{image_count} imágenes")
            return ", ".join(parts)
        if isinstance(sheet, NarrativeSheet):
            block_count = len(sheet.blocks)
            image_count = len(sheet.images)
            parts = [f"{block_count} bloques"]
            if image_count:
                parts.append(f"{image_count} imágenes")
            return ", ".join(parts)
        if isinstance(sheet, ImageSheet):
            return f"{len(sheet.images)} imágenes"
        return ""


__all__ = ["IndexRenderer"]

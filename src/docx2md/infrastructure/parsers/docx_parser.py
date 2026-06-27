"""DOCX parser adapter using python-docx."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table as DocxTable
from docx.text.paragraph import Paragraph as DocxParagraph

from docx2md.domain.entities.entities import (
    DocumentBlock,
    HeadingBlock,
    ImageBlock,
    ListItemBlock,
    ParagraphBlock,
    TableBlock,
)
from docx2md.domain.exceptions import CorruptedDocxError, ExtractionError
from docx2md.domain.ports.ports import IAssetExporter, IDocumentParser
from docx2md.domain.value_objects.value_objects import ConversionConfig


class DocxParser(IDocumentParser):
    """Parse a .docx file into logical document blocks."""

    _LIST_STYLES = {
        "List Paragraph",
        "List Bullet",
        "List Number",
        "List Bullet 2",
        "List Bullet 3",
        "List Number 2",
        "List Number 3",
    }

    def __init__(
        self,
        asset_exporter: IAssetExporter | None = None,
        config: ConversionConfig | None = None,
    ) -> None:
        self._exporter = asset_exporter
        self._config = config or ConversionConfig()
        self._img_counter = 0

    def parse(self, path: Path) -> Iterator[DocumentBlock]:
        """Iterate document elements in order of appearance."""
        try:
            doc = Document(str(path))
        except Exception as exc:
            raise CorruptedDocxError(f"cannot open {path}: {exc}") from exc

        body = doc.element.body
        for child in body:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

            if tag == "p":
                paragraph = DocxParagraph(child, doc)
                if self._config.extract_images and self._exporter is not None:
                    yield from self._extract_images_from_paragraph(paragraph, doc)

                text = self._extract_paragraph_text(paragraph)
                if not text:
                    continue

                style_name = paragraph.style.name if paragraph.style else ""
                level = self._heading_level(style_name)
                if level is not None:
                    yield HeadingBlock(level=level, text=text)
                    continue

                if self._is_list_paragraph(paragraph):
                    ordered = self._is_ordered_list(paragraph)
                    lvl = self._list_level(paragraph)
                    yield ListItemBlock(text=text, ordered=ordered, level=lvl)
                    continue

                yield ParagraphBlock(text=text)

            elif tag == "tbl" and self._config.extract_tables:
                docx_table = DocxTable(child, doc)
                yield self._parse_table(docx_table)

    def _heading_level(self, style_name: str) -> int | None:
        m = re.match(r"^[Hh]eading\s*(\d)$", style_name.strip())
        if m:
            return int(m.group(1))
        if style_name.strip().lower() == "title":
            return 1
        if style_name.strip().lower() == "subtitle":
            return 2
        return None

    def _is_ordered_list(self, paragraph: DocxParagraph) -> bool:
        p_pr = paragraph._p.find(qn("w:pPr"))
        if p_pr is None:
            return False
        num_id = p_pr.find(qn("w:numId"))
        if num_id is None:
            return False
        style = paragraph.style.name if paragraph.style else ""
        return "Number" in style

    def _list_level(self, paragraph: DocxParagraph) -> int:
        p_pr = paragraph._p.find(qn("w:pPr"))
        if p_pr is None:
            return 0
        num_pr = p_pr.find(qn("w:numPr"))
        if num_pr is None:
            return 0
        ilvl = num_pr.find(qn("w:ilvl"))
        if ilvl is None:
            return 0
        return int(ilvl.get(qn("w:val"), 0))

    def _extract_paragraph_text(self, paragraph: DocxParagraph) -> str:
        parts: list[str] = []
        for run in paragraph.runs:
            text = run.text
            if not text:
                continue
            if run.bold:
                text = f"**{text}**"
            if run.italic:
                text = f"*{text}*"
            parts.append(text)
        return "".join(parts).strip()

    def _extract_images_from_paragraph(
        self,
        paragraph: DocxParagraph,
        doc: object,
    ) -> list[ImageBlock]:
        blocks: list[ImageBlock] = []
        drawings = paragraph._p.findall(".//" + qn("w:drawing"))
        for drawing in drawings:
            blips = drawing.findall(".//" + qn("a:blip"))
            for blip in blips:
                r_id = (
                    blip.get(
                        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
                    )
                    or blip.get("{http://schemas.microsoft.com/office/2006/relationships}embed")
                )
                if not r_id or self._exporter is None:
                    continue
                try:
                    part = doc.part.related_parts[r_id]  # type: ignore[attr-defined]
                    data = part.blob
                    self._img_counter += 1
                    ext = Path(part.partname).suffix or ".png"
                    name = f"image_{self._img_counter:03d}{ext}"
                    rel_path = self._exporter.export(name, data)
                    doc_pr = drawing.find(".//" + qn("wp:docPr"))
                    alt = doc_pr.get("descr", "") if doc_pr is not None else ""
                    blocks.append(ImageBlock(filename=rel_path, alt_text=alt))
                except (KeyError, ExtractionError):
                    pass
        return blocks

    def _parse_table(self, table: DocxTable) -> TableBlock:
        rows: list[list[str]] = []
        for row in table.rows:
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            rows.append(cells)
        return TableBlock(rows=rows)

    def _is_list_paragraph(self, paragraph: DocxParagraph) -> bool:
        style = paragraph.style.name if paragraph.style else ""
        if style in self._LIST_STYLES:
            return True
        p_pr = paragraph._p.find(qn("w:pPr"))
        return p_pr is not None and p_pr.find(qn("w:numPr")) is not None


__all__ = ["DocxParser"]
